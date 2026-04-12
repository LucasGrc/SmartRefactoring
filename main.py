"""
main.py

CLI entry point for the AI-powered code refactoring tool.

Usage examples:
    python main.py refactor src/my_file.py
    python main.py refactor src/my_file.py --instructions "focus on naming"
    python main.py refactor src/my_file.py --overwrite
    python main.py batch src/
    python main.py batch src/ --recursive
    python main.py info src/my_file.py
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ── Make sure project root is importable regardless of cwd ───────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from refactor.agent import run_refactor_agent

# ── Supported extensions (mirrors server.py) ──────────────────────────────────
SUPPORTED_EXTENSIONS = {".py", ".java", ".js", ".ts"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_header(title: str) -> None:
    width = 60
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}\n")


def _print_success(msg: str) -> None:
    print(f"  ✅  {msg}")


def _print_error(msg: str) -> None:
    print(f"  ❌  {msg}", file=sys.stderr)


def _print_info(msg: str) -> None:
    print(f"  ℹ️   {msg}")


def _collect_files(path: Path, recursive: bool) -> list[Path]:
    """Return all supported source files under *path* (file or directory)."""
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [path]
        _print_error(
            f"Unsupported file type '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        return []

    if path.is_dir():
        pattern = "**/*" if recursive else "*"
        files = sorted(
            f for f in path.glob(pattern)
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        return files

    _print_error(f"Path not found: {path}")
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Command: info
# ─────────────────────────────────────────────────────────────────────────────

def cmd_info(args: argparse.Namespace) -> int:
    """Display metadata about a file without refactoring it."""
    path = Path(args.path)
    _print_header(f"File Info — {path.name}")

    if not path.exists():
        _print_error(f"File not found: {path}")
        return 1

    if not path.is_file():
        _print_error(f"Not a regular file: {path}")
        return 1

    ext       = path.suffix.lower()
    lang      = {
        ".py": "Python", ".java": "Java",
        ".js": "JavaScript", ".ts": "TypeScript",
    }.get(ext, "Unsupported")
    size_kb   = path.stat().st_size / 1024
    lines     = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    supported = ext in SUPPORTED_EXTENSIONS

    print(f"  Path      : {path.resolve()}")
    print(f"  Language  : {lang}")
    print(f"  Size      : {size_kb:.1f} KB")
    print(f"  Lines     : {lines}")
    print(f"  Supported : {'Yes' if supported else 'No'}\n")

    if not supported:
        _print_error("This file type cannot be refactored.")
        return 1

    _print_success("File is ready for refactoring.")
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Command: refactor (single file)
# ─────────────────────────────────────────────────────────────────────────────

async def _refactor_one(
    file_path: Path,
    extra_instructions: str,
    python_executable: str,
) -> bool:
    """
    Run the agent on a single file. Returns True on success, False on failure.
    """
    print(f"\n  Refactoring  →  {file_path}")
    print(f"  {'─' * 54}")

    try:
        report = await run_refactor_agent(
            file_path=str(file_path),
            extra_instructions=extra_instructions,
            python_executable=python_executable,
        )
        print(report)
        _print_success(f"Done: {file_path.name}")
        return True

    except FileNotFoundError as exc:
        _print_error(str(exc))
        return False
    except RuntimeError as exc:
        _print_error(str(exc))
        return False
    except Exception as exc:                          # noqa: BLE001
        _print_error(f"Unexpected error: {exc}")
        return False


async def _cmd_refactor_async(args: argparse.Namespace) -> int:
    path = Path(args.path)
    _print_header("Code Refactoring — Single File")

    files = _collect_files(path, recursive=False)
    if not files:
        return 1

    success = await _refactor_one(
        file_path=files[0],
        extra_instructions=args.instructions or "",
        python_executable=args.python or sys.executable,
    )
    return 0 if success else 1


def cmd_refactor(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_refactor_async(args))


# ─────────────────────────────────────────────────────────────────────────────
# Command: batch (directory)
# ─────────────────────────────────────────────────────────────────────────────

async def _cmd_batch_async(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    _print_header(f"Batch Refactoring — {directory}")

    files = _collect_files(directory, recursive=args.recursive)

    if not files:
        _print_error("No supported source files found.")
        return 1

    _print_info(f"Found {len(files)} file(s) to refactor.\n")

    results: dict[str, bool] = {}

    for idx, file_path in enumerate(files, start=1):
        print(f"[{idx}/{len(files)}] {file_path.relative_to(directory)}")
        ok = await _refactor_one(
            file_path=file_path,
            extra_instructions=args.instructions or "",
            python_executable=args.python or sys.executable,
        )
        results[str(file_path)] = ok

    # ── Summary ───────────────────────────────────────────────────────────────
    passed  = sum(1 for v in results.values() if v)
    failed  = len(results) - passed

    print(f"\n{'═' * 60}")
    print(f"  Batch complete: {passed} succeeded / {failed} failed")
    print(f"{'═' * 60}\n")

    if failed:
        print("  Failed files:")
        for fp, ok in results.items():
            if not ok:
                print(f"    • {fp}")
        return 1

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_batch_async(args))


# ─────────────────────────────────────────────────────────────────────────────
# CLI definition
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="refactor",
        description=(
            "AI-powered code refactoring tool.\n"
            "Applies SOLID principles and Clean Code practices to Python, "
            "Java, and JavaScript/TypeScript files using Claude + MCP."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py refactor src/app.py
  python main.py refactor src/app.py --instructions "focus on naming conventions"
  python main.py refactor src/Service.java --python /usr/bin/python3
  python main.py batch src/
  python main.py batch src/ --recursive --instructions "apply DRY aggressively"
  python main.py info src/app.py
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── refactor ──────────────────────────────────────────────────────────────
    p_refactor = subparsers.add_parser(
        "refactor",
        help="Refactor a single source file.",
    )
    p_refactor.add_argument(
        "path",
        help="Path to the source file to refactor.",
    )
    p_refactor.add_argument(
        "--instructions", "-i",
        metavar="TEXT",
        default="",
        help="Extra instructions passed to Claude (e.g. 'focus on naming').",
    )
    p_refactor.add_argument(
        "--python",
        metavar="PATH",
        default=None,
        help=(
            "Python interpreter used to launch the MCP server "
            "(default: current interpreter, i.e. your venv's python)."
        ),
    )
    p_refactor.set_defaults(func=cmd_refactor)

    # ── batch ─────────────────────────────────────────────────────────────────
    p_batch = subparsers.add_parser(
        "batch",
        help="Refactor all supported files in a directory.",
    )
    p_batch.add_argument(
        "directory",
        help="Directory containing the source files to refactor.",
    )
    p_batch.add_argument(
        "--recursive", "-r",
        action="store_true",
        default=False,
        help="Scan sub-directories recursively.",
    )
    p_batch.add_argument(
        "--instructions", "-i",
        metavar="TEXT",
        default="",
        help="Extra instructions applied to every file in the batch.",
    )
    p_batch.add_argument(
        "--python",
        metavar="PATH",
        default=None,
        help="Python interpreter used to launch the MCP server.",
    )
    p_batch.set_defaults(func=cmd_batch)

    # ── info ──────────────────────────────────────────────────────────────────
    p_info = subparsers.add_parser(
        "info",
        help="Show metadata about a file without refactoring it.",
    )
    p_info.add_argument(
        "path",
        help="Path to the source file to inspect.",
    )
    p_info.set_defaults(func=cmd_info)

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # ANTHROPIC_API_KEY check — fail fast with a clear message
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        _print_error(
            "ANTHROPIC_API_KEY environment variable is not set.\n"
            "  Export it before running:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()