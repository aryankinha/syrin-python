"""MCP STDIO transport — JSON-RPC 2.0 over stdin/stdout."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any, TextIO

from syrin.mcp.schema import tool_spec_to_mcp

if TYPE_CHECKING:
    from syrin.mcp.server import MCP

# MCP spec: protocolVersion 2024-11-05 is widely supported
_MCP_PROTOCOL_VERSION = "2024-11-05"

# ANSI: bold, cyan, reset
_ANSI_BOLD = "\033[1m"
_ANSI_CYAN = "\033[36m"
_ANSI_RESET = "\033[0m"


def _syrin_cli_message(*, use_color: bool = True) -> str:
    """Return highlighted Syrin CLI usage. use_color=False for non-TTY."""
    bold = _ANSI_BOLD if use_color else ""
    cyan = _ANSI_CYAN if use_color else ""
    rst = _ANSI_RESET if use_color else ""
    return (
        f"\n{bold}{cyan}  ┌─ Syrin CLI — test your MCP server{rst}\n"
        f"{bold}  │  Install: npm install -g @syrin/cli{rst}\n"
        f"{bold}  │  Test connection: syrin test --connection --url <mcp-url>{rst}\n"
        f"{bold}  │  List tools: syrin list tools --url <mcp-url>{rst}\n"
        f"{bold}  │  Find errors: syrin analyse --url <mcp-url>{rst}\n"
        f"{bold}{cyan}  └──────────────────────────────────────────────────{rst}\n"
    )


def _init_result(mcp: MCP) -> dict[str, Any]:
    """Build MCP initialize result per spec."""
    try:
        import syrin

        version = getattr(syrin, "__version__", "0.1.0")
    except ImportError:
        version = "0.1.0"
    return {
        "protocolVersion": _MCP_PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": True}},
        "serverInfo": {"name": mcp.name, "version": version},
    }


def run_stdio_mcp(
    mcp: MCP,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> None:
    """Run MCP JSON-RPC 2.0 over stdin/stdout. Blocks until EOF on stdin.

    Reads one JSON-RPC message per line from stdin. Supports tools/list and
    tools/call. Writes JSON-RPC response per line to stdout.

    Args:
        mcp: MCP server instance.
        stdin: Input stream. Defaults to sys.stdin.
        stdout: Output stream. Defaults to sys.stdout.
    """
    inp = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout

    # Developer info: Syrin CLI for testing (stderr — stdout is JSON-RPC)
    try:
        use_color = getattr(sys.stderr, "isatty", lambda: False)()
        sys.stderr.write(_syrin_cli_message(use_color=use_color))
        sys.stderr.flush()
    except Exception:
        pass

    def write_response(obj: dict[str, Any]) -> None:
        out.write(json.dumps(obj) + "\n")
        out.flush()

    for line in inp:
        line = line.strip()
        if not line:
            continue
        try:
            body = json.loads(line)
        except json.JSONDecodeError:
            write_response(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            )
            continue

        req_id = body.get("id")
        method = body.get("method", "")
        params = body.get("params") or {}

        # MCP spec: initialize must be first
        if method == "initialize":
            emit = getattr(mcp, "_emit_mcp_event", None)
            if emit:
                from syrin.enums import Hook

                emit(Hook.MCP_CONNECTED, {"method": method, "params": params})
            write_response({"jsonrpc": "2.0", "id": req_id, "result": _init_result(mcp)})
            continue
        if method == "initialized":
            write_response({"jsonrpc": "2.0", "id": req_id, "result": {}})
            continue

        if method == "tools/list":
            specs = mcp.tools()
            tools = [tool_spec_to_mcp(t) for t in specs]
            write_response({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments") or {}
            emit = getattr(mcp, "_emit_mcp_event", None)
            if emit:
                from syrin.enums import Hook

                emit(Hook.MCP_TOOL_CALL_START, {"tool_name": name, "arguments": arguments})
            for spec in mcp.tools():
                if spec.name == name:
                    try:
                        result = spec.func(**arguments)
                        content = (
                            [{"type": "text", "text": str(result)}] if result is not None else []
                        )
                        if emit:
                            emit(
                                Hook.MCP_TOOL_CALL_END,
                                {"tool_name": name, "arguments": arguments, "result": result},
                            )
                        write_response(
                            {"jsonrpc": "2.0", "id": req_id, "result": {"content": content}}
                        )
                    except Exception as e:
                        if emit:
                            emit(
                                Hook.MCP_TOOL_CALL_END,
                                {"tool_name": name, "arguments": arguments, "error": str(e)},
                            )
                        write_response(
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {"code": -32603, "message": str(e)},
                            }
                        )
                    break
            else:
                if emit:
                    emit(
                        Hook.MCP_TOOL_CALL_END,
                        {
                            "tool_name": name,
                            "arguments": arguments,
                            "error": f"Unknown tool: {name}",
                        },
                    )
                write_response(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": f"Unknown tool: {name}"},
                    }
                )
        else:
            write_response(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )

    # STDIO: client disconnected (EOF)
    emit = getattr(mcp, "_emit_mcp_event", None)
    if emit:
        from syrin.enums import Hook

        emit(Hook.MCP_DISCONNECTED, {"transport": "stdio"})
