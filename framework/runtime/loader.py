"""
YAML config loader and main run_workflow() entrypoint.

Connects workflow.yaml -> Pattern + AgentRegistry + ToolRegistry
-> OrchestrationState -> RunResult.
"""

import yaml
import time
from pathlib import Path
from typing import Any

from ..agents.base import AgentConfig
from ..agents.registry import AgentRegistry
from ..agents.concrete.stub import StubAgent
from ..orchestration.state import OrchestrationState, RunResult
from ..orchestration.patterns.base import PATTERN_REGISTRY
from ..tools.base import ToolRegistry
from ..tools.builtin.search import MockSearchTool
from ..tools.builtin.calculator import CalculatorTool
from ..tools.builtin.file_io import FileReadTool, FileWriteTool


# Maps tool type strings in YAML to the classes that implement them.
# Add new tool types here as they're built.
_TOOL_CLASSES = {
    "search":     MockSearchTool,
    "calculator": CalculatorTool,
    "file_read":  FileReadTool,
    "file_write": FileWriteTool,
}


def load_workflow_config(workflow_id: str, config_dir: str = "./configs") -> dict:
    """
    Load and parse a workflow YAML file by workflow_id.
    Looks for: {config_dir}/{workflow_id}.yaml
    """
    path = Path(config_dir) / f"{workflow_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Workflow config '{workflow_id}' not found at '{path}'."
        )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_tool_registry(tools_config: list[dict]) -> ToolRegistry:
    """Build a ToolRegistry from the tools: section of a workflow YAML."""
    registry = ToolRegistry()
    for tool_def in tools_config:
        tool_type = tool_def.get("type")
        tool_cfg = tool_def.get("config", {})
        if tool_type not in _TOOL_CLASSES:
            raise ValueError(
                f"Unknown tool type '{tool_type}'. Available: {list(_TOOL_CLASSES.keys())}"
            )
        cls = _TOOL_CLASSES[tool_type]
        try:
            instance = cls(**tool_cfg) if tool_cfg else cls()
        except TypeError:
            instance = cls()
        registry.register(instance)
    return registry


def _build_agent_registry(agents_config: list[dict]) -> AgentRegistry:
    """
    Build an AgentRegistry from the agents: section of a workflow YAML.
    Uses StubAgent for Goal 3. Concrete agents replace these in Goals 4-9.
    """
    registry = AgentRegistry()
    for agent_def in agents_config:
        config = AgentConfig(
            id=agent_def["id"],
            role=agent_def.get("role", agent_def["id"]),
            system_prompt=agent_def.get("system_prompt", ""),
            allowed_tools=agent_def.get("allowed_tools", []),
            model=agent_def.get("model", "gemma-2-9b-it"),
            max_tokens=agent_def.get("max_tokens", 2048),
            temperature=agent_def.get("temperature", 0.7),
        )
        registry.register(StubAgent(config))
    return registry


def run_workflow(
    task: str,
    workflow_id: str,
    config_dir: str = "./configs",
    config_overrides: dict | None = None,
) -> RunResult:
    """
    Main entrypoint: run a workflow from a YAML config file.

    Args:
        task:             The task string (e.g. "Summarize KV cache techniques").
        workflow_id:      Maps to {config_dir}/{workflow_id}.yaml
        config_dir:       Folder where workflow YAML files live.
        config_overrides: Optional overrides applied on top of the YAML.

    Returns:
        RunResult with status, output, message history, and trace.

    Example:
        from framework import run_workflow
        result = run_workflow("Summarize KV cache techniques", "sequential_research")
        print(result.output)
    """
    start = time.time()

    # 1. Load YAML
    try:
        raw = load_workflow_config(workflow_id, config_dir)
    except FileNotFoundError as e:
        return RunResult(run_id="error", status="failed", output="", error=str(e))

    if config_overrides:
        raw.update(config_overrides)

    # 2. Validate pattern field
    pattern_name = raw.get("pattern")
    if not pattern_name:
        return RunResult(
            run_id="error", status="failed", output="",
            error="workflow.yaml is missing required 'pattern' field."
        )

    # 3. Check pattern is registered
    if pattern_name not in PATTERN_REGISTRY:
        return RunResult(
            run_id="error", status="failed", output="",
            error=(
                f"Pattern '{pattern_name}' is not registered. "
                f"Available: {list(PATTERN_REGISTRY.keys())}. "
                f"Import the pattern module before calling run_workflow()."
            ),
        )

    # 4. Build registries
    agent_registry = _build_agent_registry(raw.get("agents", []))
    tool_registry  = _build_tool_registry(raw.get("tools", []))

    # 5. Create shared state
    state = OrchestrationState(task=task, pattern=pattern_name)

    # 6. Run the pattern
    pattern = PATTERN_REGISTRY[pattern_name]()
    try:
        result = pattern.execute(
            state=state,
            agent_registry=agent_registry,
            tool_registry=tool_registry,
        )
    except Exception as e:
        result = state.fail(error=str(e))

    result.latency_ms = (time.time() - start) * 1000
    return result
