# --------------------------------------------------------------------------
# This file's job: define the small, bounded object an agent actually receives
# at call time (as opposed to AgentConfig, which describes the agent itself).
# Built by patterns from OrchestrationState.get_context_snapshot() (see
# orchestration/state.py) plus the agent's AgentConfig.allowed_tools, and passed
# into BaseAgent.run() (agents/base.py) alongside a Task (orchestration/task.py).
# --------------------------------------------------------------------------
from dataclasses import dataclass, field


@dataclass
class AgentContext:
    """
    A bounded, structured view of OrchestrationState for a single agent call.

    Agents never receive the full OrchestrationState.
    They receive this instead — a deliberately small slice containing only
    what they need. This is the code-level enforcement of the bounded-context
    principle that prevents context blowup in parallel/swarm patterns.
    """
    run_id: str
    original_task: str
    recent_history: list[dict] = field(default_factory=list)  # [{agent, content}, ...]
    available_artifacts: list[str] = field(default_factory=list)  # names only, not contents
    allowed_tools: list[str] = field(default_factory=list)

    # @classmethod means this function receives the *class itself* (conventionally
    # named `cls`, here AgentContext) as its first argument instead of a specific
    # instance (`self`). That lets it act as an "alternate constructor": rather
    # than building an AgentContext with AgentContext(run_id=..., original_task=...)
    # directly, callers can hand it the raw snapshot dict and let this method do
    # the translation. `cls(...)` at the bottom is just calling AgentContext(...) —
    # written as `cls` instead of the literal class name so subclasses (if any)
    # would get an instance of themselves instead of hardcoded AgentContext.
    @classmethod
    def from_snapshot(cls, snapshot: dict, allowed_tools: list[str]) -> "AgentContext":
        """
        Build an AgentContext from a context_snapshot dict produced by
        OrchestrationState.get_context_snapshot().

        Why this exists: OrchestrationState.get_context_snapshot() returns a plain
        dict (cheap to build, easy to serialize). This method is the one place
        that turns that dict into the structured AgentContext object agents
        actually work with, keeping the translation logic in one spot.
        """
        return cls(
            run_id=snapshot.get("run_id", ""),
            original_task=snapshot.get("task", ""),
            recent_history=snapshot.get("recent_messages", []),
            available_artifacts=snapshot.get("artifact_names", []),
            allowed_tools=allowed_tools,
        )
