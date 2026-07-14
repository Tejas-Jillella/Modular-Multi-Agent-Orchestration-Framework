"""
Unit tests for ToolRegistry and builtin tools.
Run with: pytest tests/unit/test_tools.py -v
"""
import pytest
from framework.tools.base import BaseTool, ToolRegistry
from framework.tools.builtin.calculator import CalculatorTool
from framework.tools.builtin.search import MockSearchTool
from framework.tools.builtin.file_io import FileReadTool, FileWriteTool


# --- ToolRegistry ---

def test_register_and_get_tool():
    registry = ToolRegistry()
    calc = CalculatorTool()
    registry.register(calc)

    retrieved = registry.get("calculator")
    assert retrieved is calc


def test_get_unregistered_tool_raises_key_error():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not in registry"):
        registry.get("nonexistent_tool")


def test_invoke_allowed_tool_works():
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    result = registry.invoke(
        name="calculator",
        input="2 + 2",
        agent_id="researcher",
        allowed_tools=["calculator"],
    )
    assert result == "4"


def test_invoke_disallowed_tool_raises_permission_error():
    """An agent cannot use a tool not in its allowed_tools list."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    with pytest.raises(PermissionError, match="not allowed"):
        registry.invoke(
            name="calculator",
            input="2 + 2",
            agent_id="researcher",
            allowed_tools=["web_search"],  # calculator NOT in this list
        )


def test_get_schemas_for_agent_only_returns_allowed():
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(MockSearchTool())

    # Agent only allowed to use calculator
    schemas = registry.get_schemas_for_agent(["calculator"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "calculator"


def test_get_schemas_skips_unregistered_tools():
    """If an agent's allowed list contains a tool that wasn't registered, skip it."""
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    # "web_search" is allowed but not registered
    schemas = registry.get_schemas_for_agent(["calculator", "web_search"])
    assert len(schemas) == 1  # only calculator, not web_search


# --- CalculatorTool ---

def test_calculator_basic_arithmetic():
    calc = CalculatorTool()
    assert calc.run("2 + 2") == "4"
    assert calc.run("10 * 5") == "50"
    assert calc.run("100 / 4") == "25.0"
    assert calc.run("2 ** 8") == "256"


def test_calculator_division_by_zero():
    calc = CalculatorTool()
    result = calc.run("1 / 0")
    assert "Error" in result
    assert "zero" in result


def test_calculator_bad_expression():
    calc = CalculatorTool()
    result = calc.run("not a math expression !@#")
    assert "Error" in result


def test_calculator_to_schema_shape():
    """Tool schema must match the OpenAI-compatible function-calling format."""
    calc = CalculatorTool()
    schema = calc.to_schema()
    assert schema["type"] == "function"
    assert "function" in schema
    assert schema["function"]["name"] == "calculator"
    assert "parameters" in schema["function"]


# --- MockSearchTool ---

def test_mock_search_returns_string():
    tool = MockSearchTool()
    result = tool.run("KV cache memory")
    assert isinstance(result, str)
    assert "KV cache memory" in result


# --- FileWriteTool / FileReadTool ---

def test_file_write_and_read_roundtrip(tmp_path):
    write_tool = FileWriteTool(allowed_paths=[str(tmp_path)])
    read_tool  = FileReadTool(allowed_paths=[str(tmp_path)])

    filepath = str(tmp_path / "test_output.txt")
    content  = "Hello from the framework test."

    write_result = write_tool.run(f"{filepath}|||{content}")
    assert "Wrote" in write_result

    read_result = read_tool.run(filepath)
    assert read_result == content


def test_file_write_rejects_disallowed_path(tmp_path):
    write_tool = FileWriteTool(allowed_paths=[str(tmp_path / "safe")])
    result = write_tool.run(f"/etc/passwd|||evil content")
    assert "Error" in result


def test_file_write_requires_separator():
    write_tool = FileWriteTool()
    result = write_tool.run("no separator here")
    assert "Error" in result
    assert "|||" in result


def test_file_read_missing_file(tmp_path):
    read_tool = FileReadTool(allowed_paths=[str(tmp_path)])
    result = read_tool.run(str(tmp_path / "does_not_exist.txt"))
    assert "Error" in result
