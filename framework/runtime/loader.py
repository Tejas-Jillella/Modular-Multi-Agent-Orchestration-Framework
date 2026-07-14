"""
YAML config loader and main run_workflow() entrypoint.

Connects workflow.yaml -> Pattern + AgentRegistry + ToolRegistry
-> OrchestrationState -> RunResult.
"""

# --------------------------------------------------------------------------
# This file's job: THE GLUE. It's the one module that knows how to turn a
# workflow YAML file into a running pipeline — parsing the file, building an
# AgentRegistry (agents/registry.py) full of StubAgents
# (agents/concrete/stub.py), building a ToolRegistry (tools/base.py) full of
# built-in tools (tools/builtin/*.py), creating an OrchestrationState
# (orchestration/state.py), looking the requested pattern up in
# PATTERN_REGISTRY (orchestration/patterns/base.py), and running it. Imported
# by framework/__init__.py (which re-exports run_workflow) and by cli.py.
# --------------------------------------------------------------------------

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
    # pathlib.Path overloads Python's `/` (division) operator to mean "join a
    # path segment," so `Path(config_dir) / f"{workflow_id}.yaml"` builds a
    # path the same way os.path.join(config_dir, f"{workflow_id}.yaml") would,
    # but as a Path object with extra convenience methods (like .exists()
    # below) instead of a plain string.
    path = Path(config_dir) / f"{workflow_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Workflow config '{workflow_id}' not found at '{path}'."
        )
    with open(path, "r", encoding="utf-8") as f:
        # yaml.safe_load() parses YAML into plain Python data (dicts, lists,
        # strings, numbers) only. The alternative, yaml.load(), can — unless
        # you pass extra options — construct arbitrary Python objects
        # described in the YAML file, which is a security risk if the YAML
        # ever comes from an untrusted source (it can trigger arbitrary code
        # execution). Since workflow configs may not always be fully trusted,
        # safe_load() is the correct default here.
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
            # `**tool_cfg` unpacks a dict into keyword arguments: if
            # tool_cfg is {"allowed_paths": ["./artifacts"]}, then
            # `cls(**tool_cfg)` is exactly the same call as
            # `cls(allowed_paths=["./artifacts"])`. This lets the loader
            # construct any tool class with whatever config keys that
            # particular tool's __init__ expects, without needing to know in
            # advance what those keys are named.
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

    # 1. Load YAML — read {config_dir}/{workflow_id}.yaml off disk and parse it
    #    into a plain dict. If the file doesn't exist, there's nothing further
    #    to do: bail out immediately with a failed RunResult carrying the
    #    FileNotFoundError's message, rather than letting the exception
    #    propagate up to the caller.
    try:
        raw = load_workflow_config(workflow_id, config_dir)
    except FileNotFoundError as e:
        return RunResult(run_id="error", status="failed", output="", error=str(e))

    if config_overrides:
        raw.update(config_overrides)

    # 2. Validate pattern field — every workflow YAML must declare which
    #    pattern drives it (e.g. "sequential"). Without this field there's no
    #    way to know how to run the workflow at all, so fail fast with a clear
    #    error rather than letting a later step crash confusingly.
    pattern_name = raw.get("pattern")
    if not pattern_name:
        return RunResult(
            run_id="error", status="failed", output="",
            error="workflow.yaml is missing required 'pattern' field."
        )

    # 3. Check pattern is registered — the YAML named a pattern, but that
    #    doesn't mean a Pattern class actually exists for it: pattern modules
    #    self-register into PATTERN_REGISTRY (orchestration/patterns/base.py)
    #    only when imported, and right now (Goal 3) no pattern modules exist
    #    yet. This step catches that case with a helpful error instead of a
    #    raw KeyError later when we try to look the pattern up.
    if pattern_name not in PATTERN_REGISTRY:
        return RunResult(
            run_id="error", status="failed", output="",
            error=(
                f"Pattern '{pattern_name}' is not registered. "
                f"Available: {list(PATTERN_REGISTRY.keys())}. "
                f"Import the pattern module before calling run_workflow()."
            ),
        )

    # 4. Build registries — turn the YAML's `agents:` and `tools:` sections
    #    into an AgentRegistry (agents/registry.py, currently full of
    #    StubAgents) and a ToolRegistry (tools/base.py, real tool instances).
    #    These are what the pattern will actually dispatch work to.
    agent_registry = _build_agent_registry(raw.get("agents", []))
    tool_registry  = _build_tool_registry(raw.get("tools", []))

    # 5. Create shared state — a fresh OrchestrationState (orchestration/state.py)
    #    for this run: a new random run_id, empty message history/artifacts/
    #    trace events. This is the "game board" the pattern will read from and
    #    write to as it dispatches tasks to agents.
    state = OrchestrationState(task=task, pattern=pattern_name)

    # 6. Run the pattern — instantiate the Pattern class found in step 3 and
    #    hand it the state plus both registries; it's now fully responsible
    #    for creating Tasks, dispatching them to agents, and deciding when the
    #    run is complete. If the pattern raises any exception during
    #    execution, we don't let it propagate — we convert it into a failed
    #    RunResult via state.fail() so callers always get a RunResult back,
    #    success or failure.
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
