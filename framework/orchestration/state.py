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
    error: str | None = None


@dataclass
class OrchestrationState:
    """
    The shared game board for an entire run.

    Every pattern reads from and writes to this object.
    Agents receive a bounded slice via get_context_snapshot(),
    never the full state object directly.
    """
    task: str
    pattern: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_history: list = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    tool_call_log: list[dict] = field(default_factory=list)
    trace_events: list[dict] = field(default_factory=list)
    status: Literal["running", "complete", "failed"] = "running"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Any) -> None:
        """Append an AgentMessage and record a trace event. Always use this, never append directly."""
        self.message_history.append(message)
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
