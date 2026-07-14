# --------------------------------------------------------------------------
# This file's job: define the two objects that flow between a Pattern and an
# Agent on every single agent call — Task going in, AgentMessage coming out.
# Task is created by orchestration/patterns/*.py from OrchestrationState
# (orchestration/state.py) and consumed by BaseAgent.run() (agents/base.py,
# type-hinted only, to avoid a circular import). AgentMessage is returned by
# BaseAgent.run() implementations (e.g. agents/concrete/stub.py) and recorded
# back into OrchestrationState via add_message().
# --------------------------------------------------------------------------
import uuid
from dataclasses import dataclass, field


@dataclass
class AgentMessage:
    """
    The structured output of a single agent execution.
    Returned by BaseAgent.run() and collected by the Pattern.
    """
    agent_id: str
    role: str
    content: str
    # uuid.uuid4() generates a random, globally-unique identifier (a "Universally
    # Unique Identifier") each time it's called — that's how every message gets
    # its own message_id with no coordination needed between agents. str(...)
    # converts the UUID object to its standard hyphenated string form.
    #
    # default_factory needs a *callable* (something Python can call later, with
    # no arguments) — not an already-computed value. Writing
    # `field(default_factory=str(uuid.uuid4()))` would call uuid.uuid4() once,
    # immediately, while the class itself is being defined, and every instance
    # would then share that same fixed id — exactly the "shared mutable default"
    # bug field(default_factory=...) exists to prevent (see AgentConfig in
    # agents/base.py for the list/dict version of this same problem). Wrapping it
    # in `lambda: str(uuid.uuid4())` creates a small anonymous function that,
    # when called, runs str(uuid.uuid4()) fresh — so dataclass can call it anew
    # for every new AgentMessage, giving each one a distinct id.
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_calls: list[dict] = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class Task:
    """
    The unit of work a Pattern creates and dispatches to an agent.
    Contains a bounded context_snapshot, NOT the full OrchestrationState.

    Why agents get a Task instead of the full OrchestrationState: a Task is
    small and disposable — it carries only the instruction for this one call
    plus a pre-filtered context_snapshot dict (built by
    OrchestrationState.get_context_snapshot()). This keeps each agent call's
    prompt small and prevents an agent from reaching back into run-wide state
    it has no business touching (tool call logs, other agents' full history,
    trace events).
    """
    instruction: str
    agent_id: str
    parent_run_id: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_snapshot: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
