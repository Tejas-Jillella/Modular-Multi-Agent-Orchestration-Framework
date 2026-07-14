from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state import OrchestrationState, RunResult
    from ...agents.registry import AgentRegistry
    from ...tools.base import ToolRegistry


# Global registry — maps pattern name strings to Pattern classes.
# Populated automatically when a pattern module is imported and
# its class is decorated with @register_pattern.
PATTERN_REGISTRY: dict[str, type["BaseOrchestrationPattern"]] = {}


def register_pattern(cls: type["BaseOrchestrationPattern"]) -> type["BaseOrchestrationPattern"]:
    """
    Decorator that registers a Pattern class in PATTERN_REGISTRY.

    Usage:
        @register_pattern
        class SequentialPattern(BaseOrchestrationPattern):
            pattern_name = "sequential"
            ...

    The moment Python reads the class definition, it stores it in the
    registry under cls.pattern_name. No manual registration needed.
    """
    PATTERN_REGISTRY[cls.pattern_name] = cls
    return cls


class BaseOrchestrationPattern(ABC):
    """
    Abstract base class for all orchestration patterns.

    A Pattern is the director of a run. It creates Tasks, dispatches them
    to Agents, collects AgentMessages, updates OrchestrationState, and
    decides when execution is complete.

    Agents do not know which Pattern is running them — they only see a Task.
    """

    pattern_name: str  # set by every subclass, used as the registry lookup key

    @abstractmethod
    def execute(
        self,
        state: "OrchestrationState",
        agent_registry: "AgentRegistry",
        tool_registry: "ToolRegistry",
    ) -> "RunResult":
        """
        Execute this pattern. Must be implemented by every subclass.

        Args:
            state:          Shared OrchestrationState for this run.
            agent_registry: All agents available for this workflow.
            tool_registry:  All tools available, with permission enforcement.

        Returns:
            RunResult when execution completes (success or failure).
        """
        raise NotImplementedError

    def validate_config(self, config: dict) -> bool:
        """
        Optional config validation before execution.
        Override in subclasses that have required settings.
        Return True if valid. Raise ValueError with a message if not.
        """
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} pattern={self.pattern_name!r}>"
