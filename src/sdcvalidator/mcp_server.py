#
# Copyright 2026 Semantic Data Charter Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
"""
MCP server exposing sdcvalidator tools to any agent framework.

Implements the MCP (Model Context Protocol) as a raw JSON-RPC 2.0
stdio server. No external MCP SDK dependency.

Start the server::

    sdcvalidator serve --mcp

MCP Tools exposed:
- validate_instance: validate an XML instance against its XSD schema
- validate_and_report: detailed validation report with error classification
- check_schema_compliance: verify schema follows SDC4 principles

Protocol: JSON-RPC 2.0 over stdio (one JSON object per line).
"""

import json
import sys
from typing import Any

from sdcvalidator.validator import SDC4Validator
from sdcvalidator.schema_checker import validate_sdc4_schema_compliance

# Protocol constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "sdcvalidator"
SERVER_VERSION = "4.2.1"

# Validator cache: schema_path -> SDC4Validator
_validators: dict[str, SDC4Validator] = {}


def _get_validator(schema_path: str, check_compliance: bool = True) -> SDC4Validator:
    """Get or create a validator for the given schema."""
    key = f"{schema_path}:{check_compliance}"
    if key not in _validators:
        _validators[key] = SDC4Validator(
            schema_path,
            check_sdc4_compliance=check_compliance,
        )
    return _validators[key]


# --- Tool definitions ---

TOOLS = [
    {
        "name": "validate_instance",
        "description": (
            "Validate an XML instance against its SDC4 XSD schema. "
            "Returns pass/fail with error count and classified errors."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schema_path": {
                    "type": "string",
                    "description": "Path to the SDC4 data model XSD file.",
                },
                "instance_path": {
                    "type": "string",
                    "description": "Path to the XML instance file to validate.",
                },
                "check_compliance": {
                    "type": "boolean",
                    "description": "Check schema follows SDC4 principles (no xsd:extension). Default true.",
                    "default": True,
                },
            },
            "required": ["schema_path", "instance_path"],
        },
    },
    {
        "name": "validate_and_report",
        "description": (
            "Validate an XML instance and return a detailed report with "
            "two-tier error classification (structural vs semantic)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schema_path": {
                    "type": "string",
                    "description": "Path to the SDC4 data model XSD file.",
                },
                "instance_path": {
                    "type": "string",
                    "description": "Path to the XML instance file to validate.",
                },
                "check_compliance": {
                    "type": "boolean",
                    "description": "Check schema follows SDC4 principles. Default true.",
                    "default": True,
                },
            },
            "required": ["schema_path", "instance_path"],
        },
    },
    {
        "name": "check_schema_compliance",
        "description": (
            "Check if an XSD schema follows SDC4 principles "
            "(no xsd:extension, restriction only). Does not validate instances."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schema_path": {
                    "type": "string",
                    "description": "Path to the XSD schema file to check.",
                },
            },
            "required": ["schema_path"],
        },
    },
]


# --- Tool handlers ---

def _handle_validate_instance(args: dict[str, Any]) -> Any:
    schema_path = args["schema_path"]
    instance_path = args["instance_path"]
    check_compliance = args.get("check_compliance", True)

    try:
        validator = _get_validator(schema_path, check_compliance)
    except Exception as exc:
        return {
            "valid": False,
            "error": f"Schema error: {exc}",
            "error_count": 0,
        }

    result = validator.validate(instance_path)
    return {
        "valid": result.is_valid,
        "error_count": result.error_count,
        "structural_error_count": len(result.structural_errors),
        "semantic_error_count": len(result.semantic_errors),
    }


def _handle_validate_and_report(args: dict[str, Any]) -> Any:
    schema_path = args["schema_path"]
    instance_path = args["instance_path"]
    check_compliance = args.get("check_compliance", True)

    try:
        validator = _get_validator(schema_path, check_compliance)
    except Exception as exc:
        return {
            "valid": False,
            "error": f"Schema error: {exc}",
            "error_count": 0,
            "structural_errors": [],
            "semantic_errors": [],
        }

    return validator.validate_and_report(instance_path)


def _handle_check_schema_compliance(args: dict[str, Any]) -> Any:
    schema_path = args["schema_path"]
    is_valid, errors = validate_sdc4_schema_compliance(schema_path)
    return {
        "compliant": is_valid,
        "errors": errors,
    }


TOOL_HANDLERS = {
    "validate_instance": _handle_validate_instance,
    "validate_and_report": _handle_validate_and_report,
    "check_schema_compliance": _handle_check_schema_compliance,
}


# --- JSON-RPC 2.0 stdio server ---

def _jsonrpc_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str, data: Any = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": id, "error": error}


def _handle_request(request: dict) -> dict | None:
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        result = {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": (
                "SDC4 structural validator. Validates XML instances against "
                "XSD schemas with two-tier error classification (structural vs semantic). "
                "Independent from sdcgovernance - agents call each library separately."
            ),
        }
        return _jsonrpc_response(req_id, result)

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        return _jsonrpc_response(req_id, {"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        handler = TOOL_HANDLERS.get(tool_name)
        if handler is None:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {tool_name}")

        try:
            result = handler(tool_args)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            })
        except Exception as exc:
            return _jsonrpc_error(req_id, -32000, f"Tool execution error: {exc}")

    elif method == "ping":
        return _jsonrpc_response(req_id, {})

    else:
        if req_id is not None:
            return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")
        return None


def run_stdio() -> None:
    """Run the MCP server on stdio."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _jsonrpc_error(None, -32700, f"Parse error: {exc}")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        response = _handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def main() -> None:
    """Entry point for the sdcvalidator MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="sdcvalidator-mcp",
        description="SDC4 structural validator - MCP server",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the validation server")
    serve_parser.add_argument("--mcp", action="store_true", help="Run as MCP stdio server")

    args = parser.parse_args()

    if args.command == "serve" and args.mcp:
        run_stdio()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
