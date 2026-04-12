"""
refactor/agent.py

Connects the Claude API to the MCP server via an agentic tool-use loop.
Spawns server.py as a subprocess, fetches its tools, then runs Claude
in a loop until the refactored file has been written and a final report
is returned.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Adjust import path so this module works whether run directly or imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from prompts.solid_cleancode import SYSTEM_PROMPT, build_user_prompt

# ── Constants ─────────────────────────────────────────────────────────────────
MODEL              = "claude-sonnet-4-20250514"
MAX_TOKENS         = 8096
MAX_LOOP_TURNS     = 20          # safety cap on the agentic loop
SERVER_SCRIPT      = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_schema(schema: dict) -> dict:
    """
    Strip fields from an MCP inputSchema that the Anthropic API does not accept.
    The API only allows: type, properties, required, description, title (top-level),
    and additionalProperties. Keys like '$schema', 'default', 'examples', and
    any other JSON-Schema-only annotations cause a 400 error.
    """
    ALLOWED_TOP_LEVEL = {"type", "properties", "required", "description",
                         "title", "additionalProperties", "items", "enum",
                         "anyOf", "allOf", "oneOf"}

    clean = {k: v for k, v in schema.items() if k in ALLOWED_TOP_LEVEL}

    # Recursively sanitize nested property schemas
    if "properties" in clean and isinstance(clean["properties"], dict):
        clean["properties"] = {
            prop_name: _sanitize_property(prop_schema)
            for prop_name, prop_schema in clean["properties"].items()
        }

    # Ensure there is always a top-level "type"
    if "type" not in clean:
        clean["type"] = "object"

    return clean


def _sanitize_property(prop: dict) -> dict:
    """Sanitize a single property schema — strip JSON-Schema-only keys."""
    ALLOWED = {"type", "description", "title", "enum", "items",
               "properties", "required", "anyOf", "allOf", "oneOf",
               "additionalProperties"}
    return {k: v for k, v in prop.items() if k in ALLOWED}


def _mcp_tools_to_anthropic(mcp_tools: list) -> list[dict]:
    """
    Convert the list of MCP Tool objects returned by session.list_tools()
    into the format expected by the Anthropic messages API.
    Sanitizes inputSchema to remove fields the API rejects (e.g. '$schema').
    """
    tools = []
    for tool in mcp_tools:
        raw_schema = tool.inputSchema or {}
        if isinstance(raw_schema, dict):
            schema = _sanitize_schema(raw_schema)
        else:
            schema = {"type": "object", "properties": {}}

        tools.append({
            "name":         tool.name,
            "description":  tool.description or "",
            "input_schema": schema,
        })
        logger.debug("Tool '%s' schema: %s", tool.name, schema)

    return tools


def _extract_tool_calls(response_content: list) -> list:
    """Return only the tool_use blocks from a Claude response."""
    return [block for block in response_content if block.type == "tool_use"]


def _response_content_to_messages(response_content: list) -> list[dict]:
    """
    Serialise a Claude response's content blocks into a plain list of dicts
    suitable for appending to the messages history.
    """
    result = []
    for block in response_content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type":  "tool_use",
                "id":    block.id,
                "name":  block.name,
                "input": block.input,
            })
    return result


async def _execute_tool(session: ClientSession, tool_name: str, tool_input: dict) -> str:
    """
    Call a single MCP tool and return its result as a string.
    Handles both text and structured (JSON) responses from the server.
    """
    logger.info("Calling MCP tool: %s | input: %s", tool_name, tool_input)
    result = await session.call_tool(tool_name, arguments=tool_input)

    # Gather all text content blocks from the result
    parts = []
    for content_block in result.content:
        if hasattr(content_block, "text"):
            parts.append(content_block.text)

    raw = "\n".join(parts) if parts else ""

    # Try to pretty-print JSON so Claude can read it more easily
    try:
        parsed = json.loads(raw)
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        return raw


# ─────────────────────────────────────────────────────────────────────────────
# Core agentic loop
# ─────────────────────────────────────────────────────────────────────────────

async def run_refactor_agent(
    file_path: str,
    extra_instructions: str = "",
    python_executable: str = sys.executable,
) -> str:
    """
    Spawn the MCP server, connect to it, then run the Claude agentic loop
    until the file is refactored and a report is returned.

    Args:
        file_path:          Path to the source file to refactor.
        extra_instructions: Optional additional guidance forwarded to Claude.
        python_executable:  Python interpreter used to launch server.py.
                            Defaults to the current interpreter (respects venv).

    Returns:
        The final text response from Claude (the refactoring report).

    Raises:
        RuntimeError: If the loop exceeds MAX_LOOP_TURNS without finishing.
        FileNotFoundError: If server.py cannot be located.
    """
    if not SERVER_SCRIPT.exists():
        raise FileNotFoundError(f"MCP server script not found: {SERVER_SCRIPT}")

    # ── MCP server parameters ─────────────────────────────────────────────────
    server_params = StdioServerParameters(
        command=python_executable,
        args=[str(SERVER_SCRIPT)],
        env=None,
    )

    anthropic_client = anthropic.Anthropic()
    user_message     = build_user_prompt(file_path, extra_instructions)

    logger.info("Starting refactor agent for: %s", file_path)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # ── Initialise MCP connection ─────────────────────────────────────
            await session.initialize()
            logger.info("MCP session initialised")

            # ── Fetch tools from the MCP server ──────────────────────────────
            tools_response = await session.list_tools()
            tools          = _mcp_tools_to_anthropic(tools_response.tools)
            logger.info("Loaded %d MCP tools: %s",
                        len(tools), [t["name"] for t in tools])

            # ── Initialise conversation history ───────────────────────────────
            messages: list[dict] = [
                {"role": "user", "content": user_message}
            ]

            # ── Agentic loop ──────────────────────────────────────────────────
            for turn in range(1, MAX_LOOP_TURNS + 1):
                logger.info("── Agent turn %d/%d ──", turn, MAX_LOOP_TURNS)

                try:
                    response = anthropic_client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=SYSTEM_PROMPT,
                        tools=tools,
                        messages=messages,
                    )
                except anthropic.BadRequestError as exc:
                    logger.error("Anthropic API 400 Bad Request: %s", exc)
                    raise RuntimeError(
                        f"Anthropic API rejected the request (400): {exc}"
                    ) from exc
                except anthropic.AuthenticationError as exc:
                    raise RuntimeError(
                        "Invalid ANTHROPIC_API_KEY. Check your environment variable."
                    ) from exc
                except anthropic.RateLimitError as exc:
                    raise RuntimeError(
                        "Rate limit hit. Wait a moment and try again."
                    ) from exc
                except anthropic.APIError as exc:
                    logger.error("Anthropic API error: %s", exc)
                    raise

                logger.info(
                    "Claude response | stop_reason=%s | input_tokens=%d | output_tokens=%d",
                    response.stop_reason,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )

                # Append Claude's response to the history
                messages.append({
                    "role":    "assistant",
                    "content": _response_content_to_messages(response.content),
                })

                # ── Done — Claude produced a final text response ──────────────
                if response.stop_reason == "end_turn":
                    final_text = next(
                        (block.text for block in response.content
                         if block.type == "text"),
                        "(No text response returned)",
                    )
                    logger.info("Agent finished after %d turn(s)", turn)
                    return final_text

                # ── Tool use — execute each requested tool ────────────────────
                if response.stop_reason == "tool_use":
                    tool_calls   = _extract_tool_calls(response.content)
                    tool_results = []

                    for tool_call in tool_calls:
                        tool_output = await _execute_tool(
                            session,
                            tool_call.name,
                            tool_call.input,
                        )
                        tool_results.append({
                            "type":        "tool_result",
                            "tool_use_id": tool_call.id,
                            "content":     tool_output,
                        })
                        logger.info(
                            "Tool '%s' result (truncated): %s",
                            tool_call.name,
                            tool_output[:200],
                        )

                    # Feed results back to Claude
                    messages.append({
                        "role":    "user",
                        "content": tool_results,
                    })
                    continue

                # ── Unexpected stop reason ────────────────────────────────────
                logger.warning("Unexpected stop_reason: %s", response.stop_reason)
                break

            raise RuntimeError(
                f"Agent did not finish within {MAX_LOOP_TURNS} turns. "
                "Consider increasing MAX_LOOP_TURNS or simplifying the input file."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience sync wrapper  (useful for testing from a plain Python script)
# ─────────────────────────────────────────────────────────────────────────────

def refactor_file(
    file_path: str,
    extra_instructions: str = "",
    python_executable: str = sys.executable,
) -> str:
    """
    Synchronous wrapper around run_refactor_agent().
    Use this when you are not already inside an async context.

    Args:
        file_path:          Path to the source file to refactor.
        extra_instructions: Optional additional guidance for Claude.
        python_executable:  Python interpreter to use for the MCP server.

    Returns:
        The refactoring report produced by Claude.
    """
    return asyncio.run(
        run_refactor_agent(file_path, extra_instructions, python_executable)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quick standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent.py <path/to/file.py>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    print(f"\nRefactoring: {target}\n{'─' * 60}")

    try:
        report = refactor_file(target)
        print(report)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)