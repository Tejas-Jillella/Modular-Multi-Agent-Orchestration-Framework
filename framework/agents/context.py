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

    @classmethod
    def from_snapshot(cls, snapshot: dict, allowed_tools: list[str]) -> "AgentContext":
        """
        Build an AgentContext from a context_snapshot dict produced by
        OrchestrationState.get_context_snapshot().
        """
        return cls(
            run_id=snapshot.get("run_id", ""),
            original_task=snapshot.get("task", ""),
            recent_history=snapshot.get("recent_messages", []),
            available_artifacts=snapshot.get("artifact_names", []),
            allowed_tools=allowed_tools,
        )
