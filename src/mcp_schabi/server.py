"""
MCP Server for the Schabi homework platform.

Exposes tools to list configured children and retrieve their homework
(tasks + events) for today (or a specific date).

Multi-child support: configure several username / password / schoolClass
combinations via environment variables. The child call-name is then
passed to the get_homework tool.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from typing import Any

from fastmcp import FastMCP

from mcp_schabi.schabi_client import (
    SchabiAuthError,
    SchabiClient,
    HomeworkItem,
)


# ---------------------------------------------------------------------------
# Configuration parsing (supports multiple children)
# ---------------------------------------------------------------------------

CHILDREN: dict[str, dict[str, Any]] = {}


def _load_children_config() -> None:
    """Populate the global CHILDREN dict from environment variables.

    Supported schemes:

    1. Multi-child (recommended):
       SCHABI_CHILDREN="Emma,Lucas"
       SCHABI_EMMA_USERNAME=...
       SCHABI_EMMA_PASSWORD=...
       SCHABI_EMMA_SCHOOLCLASS=24088
       SCHABI_LUCAS_USERNAME=...
       ...

    2. Legacy single-child:
       SCHABI_USERNAME=...
       SCHABI_PASSWORD=...
       SCHABI_SCHOOLCLASS=...
    """
    global CHILDREN
    CHILDREN.clear()

    children_str = os.environ.get("SCHABI_CHILDREN", "").strip()
    if children_str:
        for raw in children_str.split(","):
            name = raw.strip()
            if not name:
                continue
            # Allow flexible env var casing for the call-name part
            uname = (
                os.environ.get(f"SCHABI_{name}_USERNAME")
                or os.environ.get(f"SCHABI_{name.upper()}_USERNAME")
                or os.environ.get(f"SCHABI_{name.lower()}_USERNAME")
            )
            pword = (
                os.environ.get(f"SCHABI_{name}_PASSWORD")
                or os.environ.get(f"SCHABI_{name.upper()}_PASSWORD")
                or os.environ.get(f"SCHABI_{name.lower()}_PASSWORD")
            )
            sc_str = (
                os.environ.get(f"SCHABI_{name}_SCHOOLCLASS")
                or os.environ.get(f"SCHABI_{name.upper()}_SCHOOLCLASS")
                or os.environ.get(f"SCHABI_{name.lower()}_SCHOOLCLASS")
                or "0"
            )
            if not uname or not pword:
                continue  # incomplete config for this child
            try:
                school_class = int(sc_str)
            except ValueError:
                school_class = 0
            CHILDREN[name] = {
                "username": uname,
                "password": pword,
                "school_class": school_class,
            }
    else:
        # Legacy single child
        username = os.environ.get("SCHABI_USERNAME", "").strip()
        password = os.environ.get("SCHABI_PASSWORD", "").strip()
        if username and password:
            sc_str = os.environ.get("SCHABI_SCHOOLCLASS", "0").strip()
            try:
                school_class = int(sc_str)
            except ValueError:
                school_class = 0
            CHILDREN["default"] = {
                "username": username,
                "password": password,
                "school_class": school_class,
            }


def _require_child(name: str) -> dict[str, Any]:
    if not CHILDREN:
        _load_children_config()
    if name not in CHILDREN:
        available = ", ".join(sorted(CHILDREN.keys())) or "<none>"
        raise ValueError(
            f"Unknown child '{name}'. Available children: {available}. "
            "Use the get_children tool to list them."
        )
    return CHILDREN[name]


def _get_client(child_name: str) -> SchabiClient:
    cfg = _require_child(child_name)
    return SchabiClient(
        username=cfg["username"],
        password=cfg["password"],
        school_class=cfg["school_class"],
    )


# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "schabi",
    instructions=(
        "MCP server for the Schabi homework platform. "
        "Use get_children to discover available kids, then get_homework for a specific child. "
        "Homework includes both pending/completed tasks and calendar events."
    ),
)


def _to_json(obj: Any) -> str:
    """Pretty-print dataclasses or lists as JSON."""
    if isinstance(obj, list):
        return json.dumps(
            [asdict(o) if hasattr(o, "__dataclass_fields__") else o for o in obj],
            ensure_ascii=False,
            indent=2,
        )
    if hasattr(obj, "__dataclass_fields__"):
        return json.dumps(asdict(obj), ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_children() -> str:
    """Return the list of configured child call-names (e.g. \"Emma\", \"Lucas\")."""
    _load_children_config()
    names = sorted(CHILDREN.keys())
    if not names:
        return "No children configured. Set SCHABI_CHILDREN and the corresponding SCHABI_<NAME>_... variables."
    return _to_json(names)


@mcp.tool()
def get_homework(child_name: str, date: str | None = None) -> str:
    """Return homework and events for the specified child.

    Args:
        child_name: Call-name returned by get_children (e.g. "Emma").
        date: Optional YYYY-MM-DD (defaults to today).

    Each item has: day, isEvent, task, done (bool or null for events).
    """
    _load_children_config()
    client = _get_client(child_name)
    try:
        items = client.get_homework(for_date=date)
        if not items:
            return f"No homework or events found for {child_name}."
        return _to_json(items)
    except SchabiAuthError as exc:
        return f"Authentication error for {child_name}: {exc}"
    except Exception as exc:  # noqa: BLE001
        return f"Error retrieving homework for {child_name}: {exc}"
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Entry point for `mcp-schabi` command (runs stdio MCP server)
# ---------------------------------------------------------------------------


def run() -> None:
    """Entry point used by the console script."""
    _load_children_config()
    # FastMCP.run() defaults to stdio transport – perfect for local MCP clients.
    mcp.run()


if __name__ == "__main__":
    run()
