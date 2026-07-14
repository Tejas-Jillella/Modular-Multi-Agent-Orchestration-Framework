# --------------------------------------------------------------------------
# This file's job: define the run-wide state object every orchestration
# pattern reads from and writes to (OrchestrationState), plus the request/
# result objects that bookend a run (RunRequest in, RunResult out).
# runtime/loader.py's run_workflow() creates an OrchestrationState and passes
# it into a Pattern's execute() (orchestration/patterns/base.py); the pattern
# calls add_message()/save_artifact()/log_tool_call() as agents run, and
# finally calls to_run_result() or fail() to produce the RunResult that
# bubbles back up to the caller (cli.py).
# --------------------------------------------------------------------------
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class RunRequest:
    """Entry point for any workflow run. Created by the user/CLI/API."""
    task: str
    pattern: str
    workflow_id: str
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Final output of a completed workflow run."""
    run_id: str
    status: str                       # "success" | "failed" | "partial"
    output: str                       # final assembled response text
    message_history: list = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    tool_call_log: list[dict] = field(default_factory=list)
    trace_events: list[dict] = field(default_factory=list)
    total_tokens: int = 0
    latency_ms: float = 0.0
    # `str | None` is a "union type": this field's value is either a str or the
    # special value None. It's Python's modern shorthand for what older code
    # spells `Optional[str]` — both mean "may be missing." Here it says error
    # defaults to None (no error) but can be set to a string message on failure.
    error: str | None = None


@dataclass
class OrchestrationState:
    """
    The shared game board for an entire run.

    Every pattern reads from and writes to this object.
    Agents receive a bounded slice via get_context_snapshot(),
    never the full state object directly.

    Why this lives here instead of in memory/: OrchestrationState is the
    run-scoped record of what actually happened (message history, artifacts,
    tool calls, trace events) — it's deliberately simple (a dataclass plus a
    handful of append/lookup methods) because right now it's the only memory
    mechanism actually wired into the pipeline. The framework/memory/ module
    (local.py, shared.py, artifacts.py) defines more capable, purpose-built
    versions of similar ideas — a scratchpad, a cross-agent key/value store, a
    disk-backed artifact store — that aren't hooked up to any pattern or agent
    yet (see Goal 10). Until they are, OrchestrationState.artifacts and
    .message_history are doing that job in a simpler, in-memory-only way.
    """
    task: str
    pattern: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_history: list = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    tool_call_log: list[dict] = field(default_factory=list)
    trace_events: list[dict] = field(default_factory=list)
    # Literal[...] restricts this field to exactly these three string values —
    # not "any str", but only "running", "complete", or "failed". A type checker
    # (or your editor) will flag `state.status = "done"` as an error, because
    # "done" isn't one of the literal options listed. It's a lightweight way to
    # get enum-like safety without defining a separate Enum class.
    status: Literal["running", "complete", "failed"] = "running"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Any) -> None:
        """
        Append an AgentMessage and record a trace event. Always use this, never
        append directly.

        Why this exists as a method instead of just `state.message_history.append(...)`
        everywhere: it keeps message_history and trace_events in sync in one
        place. If we ever need to add validation, logging, or notify listeners
        when a message arrives, this is the single choke point to change.
        """
        self.message_history.append(message)
        # getattr(obj, "attr", default) reads obj.attr but, instead of raising
        # an AttributeError if `attr` doesn't exist, returns `default`. It's used
        # here (and in get_context_snapshot below) because `message` is typed as
        # `Any` — this method doesn't strictly require a real AgentMessage, so it
        # degrades gracefully to "unknown" rather than crashing if some other
        # kind of object gets passed in.
        self.trace_events.append({
            "event": "agent_message",
            "agent_id": getattr(message, "agent_id", "unknown"),
            "message_id": getattr(message, "message_id", "unknown"),
        })

    def save_artifact(self, name: str, content: Any) -> None:
        """Store a named artifact and record a trace event."""
        self.artifacts[name] = content
        self.trace_events.append({"event": "artifact_saved", "name": name})

    def log_tool_call(self, agent_id: str, tool_name: str, input: str, result: str) -> None:
        """Record a tool invocation in the run-level tool call log."""
        self.tool_call_log.append({
            "agent_id": agent_id,
            "tool_name": tool_name,
            "input": input,
            "result": result,
        })
        self.trace_events.append({
            "event": "tool_called",
            "agent_id": agent_id,
            "tool_name": tool_name,
        })

    def get_context_snapshot(self, last_n: int = 3) -> dict:
        """
        Build a bounded context slice to pass to an agent via Task.

        This is the function that enforces "agents never see the full run
        history." Rather than handing an agent (or a Task built for it) the
        entire OrchestrationState — full message history, every tool call ever
        made, every trace event, actual artifact file contents — it
        deliberately builds a small, filtered dict: just the last N messages
        (agent name + content only, nothing else), and only the *names* of
        artifacts (not their contents). This keeps each agent's prompt bounded
        regardless of how long the run has been going, which matters a lot in
        patterns that fan out to many agents (parallel/hierarchical/swarm) —
        without this, token usage would grow unboundedly as history piles up.

        Deliberately withholds: full message history, tool call logs,
        trace events, and actual artifact contents.
        Only sends: original task, last N messages (agent + content only),
        and the names of artifacts that exist.
        """
        return {
            "run_id": self.run_id,
            "task": self.task,
            "recent_messages": [
                {
                    "agent": getattr(m, "agent_id", "unknown"),
                    "content": getattr(m, "content", ""),
                }
                # This is a list comprehension: a compact way to build a new list
                # by transforming each item from another sequence, equivalent to
                # writing a for-loop that appends to a list, but in one
                # expression. Here it walks `self.message_history[-last_n:]` and
                # produces one small {agent, content} dict per message.
                #
                # `self.message_history[-last_n:]` is list slicing: `list[-n:]`
                # means "the last n items of the list" (a negative start index
                # counts from the end, and omitting the stop index means "go to
                # the end"). E.g. with last_n=3, this takes only the most recent
                # 3 messages, discarding everything older — the actual mechanism
                # that bounds how much history an agent sees.
                for m in self.message_history[-last_n:]
            ],
            "artifact_names": list(self.artifacts.keys()),
        }

    def to_run_result(self, output: str, total_tokens: int = 0, latency_ms: float = 0.0) -> RunResult:
        """Finalize the run. Called by the Pattern when execution completes."""
        self.status = "complete"
        return RunResult(
            run_id=self.run_id,
            status="success",
            output=output,
            message_history=list(self.message_history),
            artifacts=dict(self.artifacts),
            tool_call_log=list(self.tool_call_log),
            trace_events=list(self.trace_events),
            total_tokens=total_tokens,
            latency_ms=latency_ms,
        )

    def fail(self, error: str) -> RunResult:
        """Mark the run as failed and return a RunResult."""
        self.status = "failed"
        self.trace_events.append({"event": "run_failed", "error": error})
        return RunResult(
            run_id=self.run_id,
            status="failed",
            output="",
            message_history=list(self.message_history),
            artifacts=dict(self.artifacts),
            tool_call_log=list(self.tool_call_log),
            trace_events=list(self.trace_events),
            error=error,
        )
