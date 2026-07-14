# --------------------------------------------------------------------------
# This file's job: define what an "agent" IS at the most abstract level.
# - AgentConfig is the plain-data description of an agent (loaded from workflow
#   YAML by runtime/loader.py).
# - BaseAgent is the contract every concrete agent implementation must satisfy —
#   the loader builds AgentConfig objects and hands them to agent classes (like
#   agents/concrete/stub.py's StubAgent) that inherit from BaseAgent.
# Talks to: orchestration/task.py (Task/AgentMessage types), agents/context.py
# (AgentContext), and is imported by agents/registry.py, agents/concrete/stub.py,
# and runtime/loader.py.
# --------------------------------------------------------------------------

# `dataclass`/`field` auto-generate boilerplate (like __init__) for classes that
# are mostly just data. `ABC`/`abstractmethod` let us define a class that *cannot*
# be instantiated until subclasses fill in certain methods (see BaseAgent below).
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# TYPE_CHECKING is False while the program actually runs, but tools like mypy/IDEs
# pretend it's True when analyzing the file. So the imports below never execute at
# runtime — they exist only so the string type hints ("Task", "AgentMessage",
# "AgentContext") further down can be understood by type checkers/editors.
# We do this instead of a normal import because task.py imports things that
# (indirectly) import base.py — a real import here would create an import cycle
# (base.py -> task.py -> ... -> base.py), which Python cannot resolve.
if TYPE_CHECKING:
    from ..orchestration.task import Task, AgentMessage
    from .context import AgentContext


# @dataclass is a decorator: it takes the plain class below and rewrites it to add
# an auto-generated __init__ (and __repr__, __eq__) built from the annotated
# fields, so we don't have to hand-write `def __init__(self, id, role, ...)`.
@dataclass
class AgentConfig:
    """
    Pure data describing an agent. Loaded directly from workflow YAML.
    No logic lives here — only the seven things needed to fully define an agent.

    Why this exists: runtime/loader.py parses YAML into one of these per agent
    entry, then wraps it in a concrete agent class (StubAgent for now). Keeping
    config as plain data (no behavior) makes it easy to validate, serialize, and
    swap out which agent implementation "reads" it.
    """
    id: str                                                # e.g. "researcher"
    role: str                                              # human-readable label
    system_prompt: str                                     # the LLM's persona + instructions
    # Mutable defaults (like [] or {}) can't be used directly as a default value in
    # Python — `allowed_tools: list[str] = []` would make EVERY AgentConfig instance
    # share the exact same list object, so appending to one instance's list would
    # leak into all the others. field(default_factory=list) instead tells the
    # dataclass to call list() fresh for each new instance, giving each one its own list.
    allowed_tools: list[str] = field(default_factory=list) # tool names from registry
    model: str = "gemma-2-9b-it"                          # local vLLM model
    max_tokens: int = 2048
    temperature: float = 0.7
    metadata: dict = field(default_factory=dict)          # same reasoning as above, but for a dict


# ABC ("Abstract Base Class") marks this class as a template that can't be
# instantiated on its own — `BaseAgent(config)` would raise a TypeError. Combined
# with @abstractmethod on run() below, Python enforces that only subclasses which
# actually implement run() (e.g. StubAgent) can be instantiated.
class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Every agent receives a Task and returns an AgentMessage.
    It does not know which pattern is running it, what other agents
    exist, or what happened before in the run (except what's in its
    bounded context_snapshot).

    Why this exists: it's the single contract that orchestration patterns rely on
    ("give me any object with a .run(task, context) method that returns an
    AgentMessage"). Patterns never need to know whether they're driving a
    StubAgent or a real LLM-backed agent — they just call .run().
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.id = config.id       # shortcut: agent.id instead of agent.config.id
        self.role = config.role

    # @abstractmethod marks run() as a method every concrete subclass MUST
    # override. This class only declares the method's signature and raises
    # NotImplementedError; Python's ABC machinery refuses to let anyone create a
    # BaseAgent (or a subclass that hasn't overridden run()) at all, so this
    # particular line of code is never actually reached.
    @abstractmethod
    def run(self, task: "Task", context: "AgentContext") -> "AgentMessage":
        """
        Execute this agent on the given task.

        This is the one method every agent must implement — it's the seam
        between "generic orchestration machinery" and "actual agent behavior"
        (stub output today, a real LLM call in Goals 4-9).

        Args:
            task:    Contains the instruction and bounded context_snapshot.
            context: Structured AgentContext built from task.context_snapshot.

        Returns:
            AgentMessage containing the agent's output, tool calls, and metadata.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id!r} role={self.role!r}>"
