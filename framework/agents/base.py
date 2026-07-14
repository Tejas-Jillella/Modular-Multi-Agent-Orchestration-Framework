from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..orchestration.task import Task, AgentMessage
    from .context import AgentContext


@dataclass
class AgentConfig:
    """
    Pure data describing an agent. Loaded directly from workflow YAML.
    No logic lives here — only the seven things needed to fully define an agent.
    """
    id: str                                                # e.g. "researcher"
    role: str                                              # human-readable label
    system_prompt: str                                     # the LLM's persona + instructions
    allowed_tools: list[str] = field(default_factory=list) # tool names from registry
    model: str = "gemma-2-9b-it"                          # local vLLM model
    max_tokens: int = 2048
    temperature: float = 0.7
    metadata: dict = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Every agent receives a Task and returns an AgentMessage.
    It does not know which pattern is running it, what other agents
    exist, or what happened before in the run (except what's in its
    bounded context_snapshot).
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.id = config.id       # shortcut: agent.id instead of agent.config.id
        self.role = config.role

    @abstractmethod
    def run(self, task: "Task", context: "AgentContext") -> "AgentMessage":
        """
        Execute this agent on the given task.

        Args:
            task:    Contains the instruction and bounded context_snapshot.
            context: Structured AgentContext built from task.context_snapshot.

        Returns:
            AgentMessage containing the agent's output, tool calls, and metadata.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id!r} role={self.role!r}>"
