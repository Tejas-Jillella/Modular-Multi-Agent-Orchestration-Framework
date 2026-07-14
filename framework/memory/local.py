# --------------------------------------------------------------------------
# This file's job: a per-agent scratchpad for one agent invocation (e.g. the
# back-and-forth of a single agent's own tool-call loop). NOT currently
# instantiated or used by anything in the pipeline — runtime/loader.py,
# orchestration/patterns/base.py, and agents/base.py have no references to
# this class yet. It's designed to be wired in during Goal 10, once agents
# actually need multi-turn internal state that OrchestrationState
# (orchestration/state.py) isn't meant to hold (OrchestrationState is
# run-wide and shared across all agents; this is scoped to just one agent's
# one call).
# --------------------------------------------------------------------------
from dataclasses import dataclass, field


@dataclass
class AgentLocalMemory:
    """
    Short-term memory scoped to one agent call. Not persisted.
    Cleared when the agent call ends.

    Use for: multi-turn tool-call loops, internal scratchpad notes.
    """
    agent_id: str
    scratchpad: str = ""
    turn_history: list[dict] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        """Append a message turn (role + content) to local history."""
        self.turn_history.append({"role": role, "content": content})

    def to_messages(self) -> list[dict]:
        """Return turn history in LLM message format for re-use in a follow-up call."""
        return list(self.turn_history)

    def clear(self) -> None:
        self.scratchpad = ""
        self.turn_history.clear()
