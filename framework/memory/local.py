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
