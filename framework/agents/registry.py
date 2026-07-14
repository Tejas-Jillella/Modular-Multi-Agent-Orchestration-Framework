from .base import BaseAgent


class AgentRegistry:
    """
    Stores all agent instances for a workflow run.
    Agents are looked up by their id string (e.g. "researcher").
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Add an agent. Overwrites silently if id already exists."""
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> BaseAgent:
        """Retrieve an agent by id. Raises KeyError if not found."""
        if agent_id not in self._agents:
            raise KeyError(
                f"Agent '{agent_id}' not in registry. "
                f"Registered: {list(self._agents.keys())}"
            )
        return self._agents[agent_id]

    def all(self) -> dict[str, BaseAgent]:
        """Return all agents as a {id: agent} dict."""
        return dict(self._agents)

    def ids(self) -> list[str]:
        return list(self._agents.keys())

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"<AgentRegistry agents={self.ids()!r}>"
