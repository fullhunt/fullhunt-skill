#!/usr/bin/env python3
"""Check the skill against the FullHunt API spec and MCP tool list.

Compares (method, path) pairs documented in fullhunt/references/endpoints.md with
<docs>/openapi.json, and MCP tool names in fullhunt/references/agentic-ai.md with
<docs>/contracts/mcp-tools.json (a JSON array of tool names). Exits 1 on any drift.

Usage: python3 scripts/check_drift.py --docs <path to the API docs checkout>
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "fullhunt" / "references"
METHODS = ("GET", "POST", "PUT", "DELETE")

# Documented in the skill on purpose but absent from openapi.json.
SKILL_ONLY_PATHS = set()


def normalize(path):
    path = path.split("?")[0].split("[")[0].rstrip("/")
    return re.sub(r"\{[^}]+\}", "{}", path)


def expand(path):
    """Expand one level of shell-style braces: /a/{b,c} -> /a/b, /a/c."""
    m = re.search(r"\{([^{}]*,[^{}]*)\}", path)
    if not m:
        return [path]
    return [p for alt in m.group(1).split(",") for p in expand(path[: m.start()] + alt + path[m.end():])]


def skill_routes(text):
    routes = set()
    for m in re.finditer(r"`((?:GET|POST|PUT|DELETE)(?:\|(?:GET|POST|PUT|DELETE))*|(?:POST/DELETE))?\s*(/[A-Za-z0-9_\-/{},.]+)", text):
        methods = (m.group(1) or "").replace("/", "|").split("|")
        path = m.group(2)
        if path.startswith("/oem/") and not m.group(1):
            methods = ["POST"]
        for p in expand(path):
            for meth in methods:
                if meth:
                    routes.add((meth, normalize(p)))
    return routes


def spec_routes(openapi):
    return {
        (meth.upper(), normalize(path))
        for path, ops in openapi["paths"].items()
        for meth in ops
        if meth.upper() in METHODS
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="API docs checkout containing openapi.json and contracts/mcp-tools.json")
    args = ap.parse_args()
    docs = Path(args.docs)

    openapi = json.loads((docs / "openapi.json").read_text())
    contract = json.loads((docs / "contracts" / "mcp-tools.json").read_text())

    documented = skill_routes((REFS / "endpoints.md").read_text())
    spec = spec_routes(openapi)
    unknown = sorted(r for r in documented - spec if r[1] not in SKILL_ONLY_PATHS)
    missing = sorted(spec - documented)

    tool_names = set(contract)
    agentic = (REFS / "agentic-ai.md").read_text()
    table_tools = set(re.findall(r"^\|\s*`([a-z0-9_]+)`", agentic, re.M))
    tools_unknown = sorted(table_tools - tool_names)
    tools_missing = sorted(tool_names - table_tools)

    failed = False
    for label, items in (
        ("Routes in skill but not in openapi.json", unknown),
        ("Routes in openapi.json but not in skill", missing),
        ("MCP tools in skill but not in contract", tools_unknown),
        ("MCP tools in contract but not in skill", tools_missing),
    ):
        if items:
            failed = True
            print(f"{label}:")
            for it in items:
                print("  ", " ".join(it) if isinstance(it, tuple) else it)

    print(f"routes: skill={len(documented)} spec={len(spec)}; tools: skill={len(table_tools)} contract={len(tool_names)}")
    if failed:
        return 1
    print("OK: no drift")
    return 0


if __name__ == "__main__":
    sys.exit(main())
