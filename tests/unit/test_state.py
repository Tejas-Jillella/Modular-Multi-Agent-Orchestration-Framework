"""
Unit tests for OrchestrationState, RunRequest, RunResult.
Run with: pytest tests/unit/test_state.py -v
"""
import pytest
from framework.orchestration.state import OrchestrationState, RunRequest, RunResult
from framework.orchestration.task import AgentMessage


def test_orchestration_state_creates_with_run_id():
    """Every new state object gets a unique run_id."""
    state1 = OrchestrationState(task="test task", pattern="sequential")
    state2 = OrchestrationState(task="test task", pattern="sequential")
    assert state1.run_id != state2.run_id  # UUIDs should be different


def test_orchestration_state_initial_values():
    """State starts empty and with 'running' status."""
    state = OrchestrationState(task="do something", pattern="sequential")
    assert state.task == "do something"
    assert state.pattern == "sequential"
    assert state.status == "running"
    assert state.message_history == []
    assert state.artifacts == {}
    assert state.tool_call_log == []
    assert state.trace_events == []


def test_add_message_appends_and_traces():
    """add_message() must append to history AND add a trace event."""
    state = OrchestrationState(task="t", pattern="sequential")
    msg = AgentMessage(agent_id="researcher", role="researcher", content="some output")

    state.add_message(msg)

    assert len(state.message_history) == 1
    assert state.message_history[0] is msg
    # Trace event must also be recorded
    assert len(state.trace_events) == 1
    assert state.trace_events[0]["event"] == "agent_message"
    assert state.trace_events[0]["agent_id"] == "researcher"


def test_save_artifact_stores_and_traces():
    """save_artifact() must store the artifact AND add a trace event."""
    state = OrchestrationState(task="t", pattern="sequential")
    state.save_artifact("report", "# My Report\nContent here")

    assert "report" in state.artifacts
    assert state.artifacts["report"] == "# My Report\nContent here"
    assert any(e["event"] == "artifact_saved" for e in state.trace_events)


def test_log_tool_call_records_in_log_and_trace():
    state = OrchestrationState(task="t", pattern="sequential")
    state.log_tool_call("researcher", "web_search", "KV cache", "some result")

    assert len(state.tool_call_log) == 1
    call = state.tool_call_log[0]
    assert call["agent_id"] == "researcher"
    assert call["tool_name"] == "web_search"
    assert any(e["event"] == "tool_called" for e in state.trace_events)


def test_get_context_snapshot_is_bounded():
    """Snapshot must NOT contain full history, tool logs, or artifact contents."""
    state = OrchestrationState(task="original task", pattern="sequential")
    state.save_artifact("report", "secret content")
    msg = AgentMessage(agent_id="researcher", role="researcher", content="findings")
    state.add_message(msg)

    snapshot = state.get_context_snapshot(last_n=3)

    assert snapshot["task"] == "original task"
    assert "artifact_names" in snapshot
    assert "report" in snapshot["artifact_names"]     # name is present
    assert "secret content" not in str(snapshot)      # contents are NOT
    assert "recent_messages" in snapshot
    assert len(snapshot["recent_messages"]) == 1
    # Only agent and content, not token_usage, tool_calls, etc.
    assert "token_usage" not in snapshot["recent_messages"][0]


def test_get_context_snapshot_respects_last_n():
    """Snapshot should only include the last N messages, not all of them."""
    state = OrchestrationState(task="t", pattern="sequential")
    for i in range(5):
        state.add_message(AgentMessage(agent_id=f"agent_{i}", role="worker", content=f"msg {i}"))

    snapshot = state.get_context_snapshot(last_n=2)
    assert len(snapshot["recent_messages"]) == 2
    # Should be the LAST two messages
    assert snapshot["recent_messages"][0]["agent"] == "agent_3"
    assert snapshot["recent_messages"][1]["agent"] == "agent_4"


def test_to_run_result_sets_status_complete():
    state = OrchestrationState(task="t", pattern="sequential")
    result = state.to_run_result(output="final answer", total_tokens=100)

    assert state.status == "complete"
    assert result.status == "success"
    assert result.output == "final answer"
    assert result.total_tokens == 100


def test_fail_sets_status_failed():
    state = OrchestrationState(task="t", pattern="sequential")
    result = state.fail(error="something went wrong")

    assert state.status == "failed"
    assert result.status == "failed"
    assert result.error == "something went wrong"
    assert result.output == ""
