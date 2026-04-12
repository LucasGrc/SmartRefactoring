"""
MCP Server for Code Refactoring
Exposes tools to read, write, validate, and inspect source code files
for use by the Claude-powered refactoring agent.
"""

import sys
import os
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# ── Logging (stderr only — stdout is reserved for MCP JSON-RPC) ──────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Supported languages ───────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".py":   "python",
    ".java": "java",
    ".js":   "javascript",
    ".ts":   "typescript",
}

MAX_FILE_SIZE_BYTES = 500_000  # 500 KB safety limit

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP(
    "code-refactor-server",
    instructions=(
        "Provides file I/O and inspection tools that let a refactoring agent "
        "read source code, analyse it, and persist the improved version."
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Tool: detect_language
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def detect_language(file_path: str) -> dict:
    """
    Detect the programming language of a source file from its extension.

    Args:
        file_path: Absolute or relative path to the source file.

    Returns:
        A dict with keys:
          - language (str): "python" | "java" | "javascript" | "typescript"
          - extension (str): the file extension found
          - supported (bool): whether the language can be refactored
    """
    path = Path(file_path)
    ext  = path.suffix.lower()
    lang = SUPPORTED_EXTENSIONS.get(ext)

    logger.info("detect_language: %s → ext=%s lang=%s", file_path, ext, lang)

    return {
        "language":  lang or "unknown",
        "extension": ext,
        "supported": lang is not None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool: read_file
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def read_file(file_path: str) -> dict:
    """
    Read the full content of a source code file from disk.

    Args:
        file_path: Absolute or relative path to the file to read.

    Returns:
        A dict with keys:
          - content (str): the file's text content
          - language (str): detected programming language
          - lines (int): total number of lines
          - file_name (str): base name of the file
          - error (str | None): error message if the read failed
    """
    path = Path(file_path)

    if not path.exists():
        msg = f"File not found: {file_path}"
        logger.error(msg)
        return {"content": "", "language": "unknown", "lines": 0,
                "file_name": path.name, "error": msg}

    if not path.is_file():
        msg = f"Path is not a regular file: {file_path}"
        logger.error(msg)
        return {"content": "", "language": "unknown", "lines": 0,
                "file_name": path.name, "error": msg}

    size = path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        msg = (f"File too large ({size} bytes). "
               f"Maximum allowed is {MAX_FILE_SIZE_BYTES} bytes.")
        logger.error(msg)
        return {"content": "", "language": "unknown", "lines": 0,
                "file_name": path.name, "error": msg}

    ext      = path.suffix.lower()
    language = SUPPORTED_EXTENSIONS.get(ext, "unknown")

    if language == "unknown":
        msg = (f"Unsupported file extension '{ext}'. "
               f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        logger.warning(msg)
        return {"content": "", "language": "unknown", "lines": 0,
                "file_name": path.name, "error": msg}

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")
        logger.warning("read_file: fell back to latin-1 for %s", file_path)

    line_count = len(content.splitlines())
    logger.info("read_file: %s (%s, %d lines)", file_path, language, line_count)

    return {
        "content":   content,
        "language":  language,
        "lines":     line_count,
        "file_name": path.name,
        "error":     None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool: write_file
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def write_file(file_path: str, content: str, overwrite: bool = False) -> dict:
    """
    Write refactored source code to a file on disk.

    If overwrite is False (default) and the file already exists, a new file
    is created automatically with a '_refactored' suffix so the original is
    never lost.

    Args:
        file_path: Desired output path for the refactored file.
        content:   The refactored source code string.
        overwrite: If True, replace the existing file. Default False.

    Returns:
        A dict with keys:
          - success (bool)
          - output_path (str): the path that was actually written
          - message (str): human-readable status
          - error (str | None)
    """
    path = Path(file_path)

    # Auto-rename to avoid overwriting the original
    if path.exists() and not overwrite:
        stem     = path.stem
        suffix   = path.suffix
        new_name = f"{stem}_refactored{suffix}"
        path     = path.parent / new_name
        logger.info("write_file: original exists — writing to %s instead", path)

    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        path.write_text(content, encoding="utf-8")
        msg = f"File written successfully: {path}"
        logger.info(msg)
        return {"success": True, "output_path": str(path),
                "message": msg, "error": None}
    except OSError as exc:
        msg = f"Failed to write {path}: {exc}"
        logger.error(msg)
        return {"success": False, "output_path": str(path),
                "message": msg, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Tool: get_file_info
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_file_info(file_path: str) -> dict:
    """
    Return metadata about a source file without reading its content.
    Useful for quick sanity-checks before committing to a full read.

    Args:
        file_path: Path to the source file.

    Returns:
        A dict with keys:
          - exists (bool)
          - file_name (str)
          - language (str)
          - extension (str)
          - size_bytes (int)
          - supported (bool)
          - error (str | None)
    """
    path = Path(file_path)
    ext  = path.suffix.lower()
    lang = SUPPORTED_EXTENSIONS.get(ext)

    if not path.exists():
        return {
            "exists":     False,
            "file_name":  path.name,
            "language":   lang or "unknown",
            "extension":  ext,
            "size_bytes": 0,
            "supported":  False,
            "error":      f"File not found: {file_path}",
        }

    return {
        "exists":     True,
        "file_name":  path.name,
        "language":   lang or "unknown",
        "extension":  ext,
        "size_bytes": path.stat().st_size,
        "supported":  lang is not None,
        "error":      None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool: list_files
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def list_files(directory: str, recursive: bool = False) -> dict:
    """
    List all supported source files inside a directory.
    Handy when you want to batch-refactor a whole project.

    Args:
        directory: Path to the directory to scan.
        recursive: If True, scan sub-directories as well. Default False.

    Returns:
        A dict with keys:
          - files (list[str]): paths of supported source files
          - count (int): total number of files found
          - error (str | None)
    """
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        msg = f"Directory not found: {directory}"
        logger.error(msg)
        return {"files": [], "count": 0, "error": msg}

    pattern = "**/*" if recursive else "*"
    found: list[str] = []

    for item in dir_path.glob(pattern):
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(str(item))

    found.sort()
    logger.info("list_files: %d supported files found in %s", len(found), directory)
    return {"files": found, "count": len(found), "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting code-refactor MCP server (stdio transport)…")
    mcp.run(transport="stdio")