# --------------------------------------------------------------------------
# This file's job: hold all the agent instances built for one workflow run and
# let patterns look them up by id string. Built by runtime/loader.py's
# _build_agent_registry() and handed to a Pattern's execute() method
# (orchestration/patterns/base.py) alongside a ToolRegistry (tools/base.py).
# --------------------------------------------------------------------------
from .base import BaseAgent


class AgentRegistry:
    """
    Stores all agent instances for a workflow run.
    Agents are looked up by their id string (e.g. "researcher").

    Why a registry instead of just passing agents around directly: a workflow
    can have any number of agents (defined dynamically from YAML), and patterns
    need to look one up by name at run time (e.g. "dispatch this task to the
    'researcher' agent") without every piece of code needing its own reference
    to every agent object. Centralizing lookup in one place also makes it a
    single spot to add validation, logging, or permission checks later.
    """

    def __init__(self):
        # A leading underscore (`_agents`) is a Python naming convention (not
        # enforced by the language itself) signaling "this is internal — treat it
        # as private." Callers are expected to go through the public methods below
        # (register/get/all/ids) instead of reaching into _agents directly, so the
        # internal storage (a dict here) could be swapped out later without
        # breaking anyone who uses this class.
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

    # __len__ is a "dunder" (double-underscore) method — Python calls it
    # automatically when you write `len(some_registry)`, instead of requiring
    # `some_registry.get_length()`. Defining it lets AgentRegistry behave like a
    # built-in container (list, dict) for this one operation.
    def __len__(self) -> int:
        return len(self._agents)

    # __repr__ is another dunder method: Python calls it to build the string
    # shown when you print() an object or inspect it in a debugger/REPL. Without
    # it you'd see a generic `<AgentRegistry object at 0x...>`; with it you get
    # something readable like `<AgentRegistry agents=['researcher', 'writer']>`.
    def __repr__(self) -> str:
        return f"<AgentRegistry agents={self.ids()!r}>"
