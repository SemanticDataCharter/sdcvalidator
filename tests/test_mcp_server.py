#
# Copyright 2026 Semantic Data Charter Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
"""
Tests for MCP server - JSON-RPC 2.0 protocol and tool definitions.
"""

import json
import pytest
from pathlib import Path
from sdcvalidator.mcp_server import _handle_request, TOOLS, TOOL_HANDLERS

TEST_DATA_DIR = Path(__file__).parent / "test_data"


def call_tool(name: str, arguments: dict) -> dict:
    """Helper: call an MCP tool via JSON-RPC and return parsed result."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    response = _handle_request(request)
    assert "result" in response, f"Expected result, got: {response}"
    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    return json.loads(content[0]["text"])


class TestMcpProtocol:
    """JSON-RPC 2.0 MCP protocol handling."""

    def test_initialize(self):
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        response = _handle_request(request)
        assert response["id"] == 1
        result = response["result"]
        assert result["serverInfo"]["name"] == "sdcvalidator"
        assert "tools" in result["capabilities"]

    def test_initialized_notification(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        response = _handle_request(request)
        assert response is None

    def test_tools_list(self):
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        response = _handle_request(request)
        tools = response["result"]["tools"]
        assert len(tools) == 3
        names = {t["name"] for t in tools}
        assert names == {"validate_instance", "validate_and_report", "check_schema_compliance"}

    def test_tools_have_input_schemas(self):
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
        response = _handle_request(request)
        for tool in response["result"]["tools"]:
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_ping(self):
        request = {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
        response = _handle_request(request)
        assert response["id"] == 4
        assert response["result"] == {}

    def test_unknown_method(self):
        request = {"jsonrpc": "2.0", "id": 5, "method": "nonexistent", "params": {}}
        response = _handle_request(request)
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_unknown_tool(self):
        request = {
            "jsonrpc": "2.0", "id": 6,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }
        response = _handle_request(request)
        assert "error" in response
        assert "Unknown tool" in response["error"]["message"]


class TestCheckSchemaCompliance:
    """check_schema_compliance MCP tool."""

    def test_valid_schema(self):
        data = call_tool("check_schema_compliance", {
            "schema_path": str(TEST_DATA_DIR / "valid_sdc4_schema.xsd"),
        })
        assert data["compliant"] is True
        assert data["errors"] == []

    def test_invalid_schema_with_extension(self):
        data = call_tool("check_schema_compliance", {
            "schema_path": str(TEST_DATA_DIR / "invalid_sdc4_schema_with_extension.xsd"),
        })
        assert data["compliant"] is False
        assert len(data["errors"]) > 0
        assert any("extension" in e.lower() for e in data["errors"])

    def test_non_sdc4_schema_passes(self):
        data = call_tool("check_schema_compliance", {
            "schema_path": str(TEST_DATA_DIR / "non_sdc4_schema_with_extension.xsd"),
        })
        assert data["compliant"] is True

    def test_nonexistent_file(self):
        data = call_tool("check_schema_compliance", {
            "schema_path": "/nonexistent/path/schema.xsd",
        })
        assert data["compliant"] is False
        assert any("not found" in e.lower() for e in data["errors"])


class TestConsistentSerialization:
    """Verify all tools return consistent JSON-RPC format."""

    def test_all_tools_return_single_text_content(self):
        """Every tool returns exactly one content block with type=text."""
        test_calls = [
            ("check_schema_compliance", {"schema_path": str(TEST_DATA_DIR / "valid_sdc4_schema.xsd")}),
        ]
        for tool_name, args in test_calls:
            request = {
                "jsonrpc": "2.0", "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args},
            }
            response = _handle_request(request)
            assert "result" in response, f"{tool_name} returned error: {response}"
            content = response["result"]["content"]
            assert len(content) == 1, f"{tool_name} returned {len(content)} content blocks"
            assert content[0]["type"] == "text"
            parsed = json.loads(content[0]["text"])
            assert parsed is not None

class TestMalformedRequestsDoNotKillTheServer:
    """
    VSL rollout inventory R9. Six inputs that are valid JSON but not a
    JSON-RPC request raised AttributeError in _handle_request and ended the
    process. Each is now answered with -32600 (or -32602 for bad tool params)
    and the loop keeps reading.
    """

    @pytest.mark.parametrize("payload", [[], ["tools/list"], "tools/list", 7, None, True])
    def test_a_non_object_request_is_invalid_request(self, payload):
        response = _handle_request(payload)
        assert response["error"]["code"] == -32600
        assert response["id"] is None

    @pytest.mark.parametrize("params", [[], "x", 3, True])
    def test_non_object_params_are_invalid_request(self, params):
        response = _handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": params})
        assert response["error"]["code"] == -32600
        assert response["id"] == 1

    def test_null_params_are_treated_as_empty(self):
        response = _handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": None})
        assert "result" in response

    def test_a_non_string_method_is_invalid_request(self):
        response = _handle_request({"jsonrpc": "2.0", "id": 1, "method": ["tools/list"]})
        assert response["error"]["code"] == -32600

    @pytest.mark.parametrize("arguments", [[], "x", 3])
    def test_non_object_tool_arguments_are_invalid_params(self, arguments):
        response = _handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": list(TOOL_HANDLERS)[0], "arguments": arguments},
        })
        assert response["error"]["code"] == -32602

    def test_the_stdio_loop_survives_every_one_of_them(self, monkeypatch, capsys):
        import io
        import sys

        from sdcvalidator.mcp_server import run_stdio

        lines = ["[]", "\"tools/list\"", "7", "null",
                 json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": []}),
                 json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"})]
        monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(lines) + "\n"))
        run_stdio()
        out = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines()]
        assert len(out) == 6
        assert [o.get("error", {}).get("code") for o in out[:5]] == [-32600] * 5
        assert out[5] == {"jsonrpc": "2.0", "id": 2, "result": {}}
