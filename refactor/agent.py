"""
refactor/agent.py

Connects either the Claude API (default) or a local Ollama model (--local)
to the MCP server via an agentic tool-use loop.

Spawns server.py as a subprocess, fetches its tools, then runs the model
in a loop until the refactored file has been written and a final report
is returned.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import anthropic
from openai import OpenAI                          # used for Ollama local mode
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Adjust import path so this module works whether run directly or imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from prompts.solid_cleancode import SYSTEM_PROMPT, build_user_prompt

# ── Constants ─────────────────────────────────────────────────────────────────
ANTHROPIC_MODEL    = "claude-sonnet-4-20250514"
LOCAL_MODEL        = "qwen2.5-coder:14b"          # change to match your ollama pull
OLLAMA_BASE_URL    = "http://localhost:11434/v1"
MAX_TOKENS         = 8096
MAX_LOOP_TURNS     = 20
SERVER_SCRIPT      = Path(__file__).resolve().parent.parent / "mcp_server" / "server.py"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Schema helpers (shared by both modes)
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_schema(schema: dict) -> dict:
    """Strip JSON-Schema-only keys that APIs reject (e.g. '$schema', 'default')."""
    ALLOWED = {"type", "properties", "required", "description",
               "title", "additionalProperties", "items", "enum",
               "anyOf", "allOf", "oneOf"}
    clean = {k: v for k, v in schema.items() if k in ALLOWED}
    if "properties" in clean and isinstance(clean["properties"], dict):
        clean["properties"] = {
            name: _sanitize_property(prop)
            for name, prop in clean["properties"].items()
        }
    if "type" not in clean:
        clean["type"] = "object"
    return clean


def _sanitize_property(prop: dict) -> dict:
    ALLOWED = {"type", "description", "title", "enum", "items",
               "properties", "required", "anyOf", "allOf", "oneOf",
               "additionalProperties"}
    return {k: v for k, v in prop.items() if k in ALLOWED}


# ─────────────────────────────────────────────────────────────────────────────
# Tool format converters
# ─────────────────────────────────────────────────────────────────────────────

def _mcp_tools_to_anthropic(mcp_tools: list) -> list[dict]:
    """Convert MCP tools → Anthropic messages API format."""
    tools = []
    for tool in mcp_tools:
        raw = tool.inputSchema or {}
        schema = _sanitize_schema(raw) if isinstance(raw, dict) else {"type": "object", "properties": {}}
        tools.append({
            "name":         tool.name,
            "description":  tool.description or "",
            "input_schema": schema,
        })
        logger.debug("Anthropic tool '%s' schema ready", tool.name)
    return tools


def _mcp_tools_to_openai(mcp_tools: list) -> list[dict]:
    """Convert MCP tools → OpenAI/Ollama chat completions format."""
    tools = []
    for tool in mcp_tools:
        raw = tool.inputSchema or {}
        schema = _sanitize_schema(raw) if isinstance(raw, dict) else {"type": "object", "properties": {}}
        tools.append({
            "type": "function",
            "function": {
                "name":        tool.name,
                "description": tool.description or "",
                "parameters":  schema,          # same content, different key name
            },
        })
        logger.debug("Ollama tool '%s' schema ready", tool.name)
    return tools


# ─────────────────────────────────────────────────────────────────────────────
# Shared MCP tool executor
# ─────────────────────────────────────────────────────────────────────────────

async def _execute_tool(session: ClientSession, tool_name: str, tool_input: dict) -> str:
    """Call a single MCP tool and return its result as a pretty-printed string."""
    logger.info("Calling MCP tool: %s | input: %s", tool_name, tool_input)
    result = await session.call_tool(tool_name, arguments=tool_input)

    parts = [cb.text for cb in result.content if hasattr(cb, "text")]
    raw = "\n".join(parts) if parts else ""

    try:
        return json.dumps(json.loads(raw), indent=2)
    except (json.JSONDecodeError, TypeError):
        return raw


# ─────────────────────────────────────────────────────────────────────────────
# Anthropic agentic loop
# ─────────────────────────────────────────────────────────────────────────────

async def _run_anthropic_loop(
    session: ClientSession,
    mcp_tools: list,
    user_message: str,
) -> str:
    """Run the agentic loop using the Anthropic API."""
    client   = anthropic.Anthropic()
    tools    = _mcp_tools_to_anthropic(mcp_tools)
    messages: list[dict] = [{"role": "user", "content": user_message}]

    for turn in range(1, MAX_LOOP_TURNS + 1):
        logger.info("── Anthropic turn %d/%d ──", turn, MAX_LOOP_TURNS)

        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
        except anthropic.BadRequestError as exc:
            logger.error("Anthropic 400: %s", exc)
            raise RuntimeError(f"Anthropic API rejected the request (400): {exc}") from exc
        except anthropic.AuthenticationError as exc:
            raise RuntimeError("Invalid ANTHROPIC_API_KEY. Check your environment variable.") from exc
        except anthropic.RateLimitError as exc:
            raise RuntimeError("Rate limit hit. Wait a moment and try again.") from exc
        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise

        logger.info(
            "Response | stop_reason=%s | in=%d out=%d tokens",
            response.stop_reason,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        # Append assistant turn to history
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input,
                })
        messages.append({"role": "assistant", "content": assistant_content})

        # Done
        if response.stop_reason == "end_turn":
            final = next((b.text for b in response.content if b.type == "text"), "(No text)")
            logger.info("Anthropic agent finished after %d turn(s)", turn)
            return final

        # Tool use
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    output = await _execute_tool(session, block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    })
                    logger.info("Tool '%s' result (truncated): %s", block.name, output[:200])
            messages.append({"role": "user", "content": tool_results})
            continue

        logger.warning("Unexpected stop_reason: %s", response.stop_reason)
        break

    raise RuntimeError(
        f"Agent did not finish within {MAX_LOOP_TURNS} turns. "
        "Consider increasing MAX_LOOP_TURNS or simplifying the input file."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ollama (local) agentic loop
# ─────────────────────────────────────────────────────────────────────────────

async def _run_ollama_loop(
    session: ClientSession,
    mcp_tools: list,
    user_message: str,
) -> str:
    """Run the agentic loop using a local Ollama model via OpenAI-compatible API."""
    client   = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    tools    = _mcp_tools_to_openai(mcp_tools)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ]

    for turn in range(1, MAX_LOOP_TURNS + 1):
        logger.info("── Ollama turn %d/%d ──", turn, MAX_LOOP_TURNS)

        try:
            response = client.chat.completions.create(
                model=LOCAL_MODEL,
                max_tokens=MAX_TOKENS,
                tools=tools,
                messages=messages,
            )
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
            raise RuntimeError(
                f"Ollama request failed: {exc}\n"
                "Make sure Ollama is running:  ollama serve\n"
                f"And the model is pulled:      ollama pull {LOCAL_MODEL}"
            ) from exc

        choice = response.choices[0]
        logger.info(
            "Response | finish_reason=%s | in=%d out=%d tokens",
            choice.finish_reason,
            response.usage.prompt_tokens if response.usage else 0,
            response.usage.completion_tokens if response.usage else 0,
        )

        # Append assistant turn (OpenAI format)
        tool_calls_payload = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name":      tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in (choice.message.tool_calls or [])
        ]
        messages.append({
            "role":       "assistant",
            "content":    choice.message.content,
            "tool_calls": tool_calls_payload or None,
        })

        # Done
        if choice.finish_reason == "stop":
            final = choice.message.content or "(No text response returned)"
            logger.info("Ollama agent finished after %d turn(s)", turn)
            return final

        # Tool use
        if choice.finish_reason == "tool_calls":
            for tool_call in (choice.message.tool_calls or []):
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}

                output = await _execute_tool(
                    session, tool_call.function.name, tool_input
                )
                logger.info(
                    "Tool '%s' result (truncated): %s",
                    tool_call.function.name,
                    output[:200],
                )
                # Each tool result is its own message in OpenAI format
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      output,
                })
            continue

        logger.warning("Unexpected finish_reason: %s", choice.finish_reason)
        break

    raise RuntimeError(
        f"Agent did not finish within {MAX_LOOP_TURNS} turns. "
        "Consider increasing MAX_LOOP_TURNS or simplifying the input file."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_refactor_agent(
    file_path: str,
    extra_instructions: str = "",
    python_executable: str = sys.executable,
    use_local: bool = False,
) -> str:
    """
    Spawn the MCP server, connect to it, then run the agentic loop.

    Args:
        file_path:          Path to the source file to refactor.
        extra_instructions: Optional additional guidance for the model.
        python_executable:  Python interpreter used to launch server.py.
        use_local:          If True, use local Ollama instead of Claude API.

    Returns:
        The final refactoring report as a string.
    """
    if not SERVER_SCRIPT.exists():
        raise FileNotFoundError(f"MCP server script not found: {SERVER_SCRIPT}")

    mode = "Ollama (local)" if use_local else "Claude API"
    logger.info("Starting refactor agent [%s] for: %s", mode, file_path)

    server_params = StdioServerParameters(
        command=python_executable,
        args=[str(SERVER_SCRIPT)],
        env=None,
    )
    user_message = build_user_prompt(file_path, extra_instructions)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP session initialised")

            tools_response = await session.list_tools()
            logger.info(
                "Loaded %d MCP tools: %s",
                len(tools_response.tools),
                [t.name for t in tools_response.tools],
            )

            if use_local:
                return await _run_ollama_loop(
                    session, tools_response.tools, user_message
                )
            else:
                return await _run_anthropic_loop(
                    session, tools_response.tools, user_message
                )


# ─────────────────────────────────────────────────────────────────────────────
# Sync wrapper
# ─────────────────────────────────────────────────────────────────────────────

def refactor_file(
    file_path: str,
    extra_instructions: str = "",
    python_executable: str = sys.executable,
    use_local: bool = False,
) -> str:
    """Synchronous wrapper around run_refactor_agent()."""
    return asyncio.run(
        run_refactor_agent(file_path, extra_instructions, python_executable, use_local)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Quick standalone test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse as _ap
    parser = _ap.ArgumentParser()
    parser.add_argument("path", help="Source file to refactor")
    parser.add_argument("--local", action="store_true", help="Use local Ollama model")
    ns = parser.parse_args()

    print(f"\nRefactoring: {ns.path}  [{'local' if ns.local else 'cloud'}]\n{'─' * 60}")
    try:
        print(refactor_file(ns.path, use_local=ns.local))
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
