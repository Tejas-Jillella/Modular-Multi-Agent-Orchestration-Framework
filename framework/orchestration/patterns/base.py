# --------------------------------------------------------------------------
# This file's job: define what an orchestration "pattern" IS (the abstract
# contract, BaseOrchestrationPattern) and provide the self-registration
# mechanism (PATTERN_REGISTRY + @register_pattern) that lets runtime/loader.py
# find a pattern by name string without hardcoding a list of pattern classes.
# Concrete patterns (sequential, parallel, router, etc. — added in later goals)
# will live in sibling files in this package and import BaseOrchestrationPattern
# and register_pattern from here.
# --------------------------------------------------------------------------
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# See agents/base.py for a full explanation of TYPE_CHECKING — same reasoning
# applies here: these imports only exist for type hints, avoiding a circular
# import at runtime (this module is imported very early, before state.py's
# other consumers exist).
if TYPE_CHECKING:
    from ..state import OrchestrationState, RunResult
    from ...agents.registry import AgentRegistry
    from ...tools.base import ToolRegistry


# Global registry — maps pattern name strings to Pattern classes.
# Populated automatically when a pattern module is imported and
# its class is decorated with @register_pattern.
#
# Why self-registration instead of runtime/loader.py hardcoding "if pattern ==
# 'sequential': use SequentialPattern, elif ...": that would mean editing
# loader.py every time a new pattern is added, and loader.py would need to
# import every pattern module whether or not a given run uses it. Instead,
# each pattern file registers itself the moment it's imported (see
# @register_pattern below), so adding a new pattern means adding a new file —
# no changes to the loader.
#
# Why PATTERN_REGISTRY starts empty: no pattern modules have been written yet
# (this is Goal 3, the skeleton) — sequential/router/parallel/hierarchical/
# etc. are added in Goals 4-9. Until those files exist and get imported
# somewhere, this dict has nothing in it, and runtime/loader.py's
# run_workflow() correctly reports "pattern not registered" for any workflow.
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

    Mechanically, `@register_pattern` above a class definition is exactly
    equivalent to writing, right after the class body:
        SequentialPattern = register_pattern(SequentialPattern)
    Python defines the class first, then immediately passes that class object
    into register_pattern() as `cls`, and rebinds the name (SequentialPattern)
    to whatever register_pattern() returns. This function stores the class in
    PATTERN_REGISTRY as a side effect, then returns the same class unchanged —
    so the decorator's only visible effect is "this class is now registered,"
    and the class continues to work exactly as if the decorator weren't there.
    This all happens once, at import time (when Python first reads the module
    containing the class) — not each time the class is instantiated.
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
