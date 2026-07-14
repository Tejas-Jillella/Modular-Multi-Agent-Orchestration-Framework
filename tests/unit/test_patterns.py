"""
Unit tests for the pattern registry and BaseOrchestrationPattern.
Run with: pytest tests/unit/test_patterns.py -v
"""
import pytest
from framework.orchestration.patterns.base import (
    PATTERN_REGISTRY,
    BaseOrchestrationPattern,
    register_pattern,
)
from framework.orchestration.state import OrchestrationState, RunResult
from framework.agents.registry import AgentRegistry
from framework.tools.base import ToolRegistry


# --- Test the registry mechanism itself ---

def test_register_pattern_decorator_adds_to_registry():
    """@register_pattern must add the class to PATTERN_REGISTRY under pattern_name."""

    # _TestPattern is defined INSIDE this test function, not at module level,
    # because PATTERN_REGISTRY (orchestration/patterns/base.py) is a single
    # global dict shared by the whole test process. If this class were defined
    # at the top of the file, decorating it with @register_pattern would
    # register it into PATTERN_REGISTRY the moment this test file is imported
    # — and it would stay there for every other test that runs afterward,
    # potentially colliding with pattern names other tests expect to be empty
    # or absent. Defining it locally means it only gets created (and
    # registered) while this specific test function is executing.
    @register_pattern
    class _TestPattern(BaseOrchestrationPattern):
        pattern_name = "_test_pattern_unique"

        def execute(self, state, agent_registry, tool_registry):
            return state.to_run_result(output="test done")

    assert "_test_pattern_unique" in PATTERN_REGISTRY
    # `is` checks identity, not equality: this confirms PATTERN_REGISTRY
    # stored the exact _TestPattern class object the decorator was applied
    # to, not merely something that looks the same.
    assert PATTERN_REGISTRY["_test_pattern_unique"] is _TestPattern

    # Clean up so this test doesn't bleed into others. Even though the class
    # was defined locally, @register_pattern still wrote it into the shared,
    # module-level PATTERN_REGISTRY dict — that side effect outlives this
    # function's local scope. Without this `del`, "_test_pattern_unique"
    # would remain registered for every test that runs after this one in the
    # same process (pytest doesn't reset module-level state between tests),
    # so later tests could see registry state left over from this one.
    del PATTERN_REGISTRY["_test_pattern_unique"]


def test_unregistered_pattern_not_in_registry():
    assert "definitely_not_a_pattern" not in PATTERN_REGISTRY


def test_registered_pattern_is_instantiable():
    """A registered pattern class should be instantiable and callable."""

    # Same reasoning as _TestPattern above: defined locally so this
    # registration doesn't leak into PATTERN_REGISTRY for other tests.
    @register_pattern
    class _InstantiablePattern(BaseOrchestrationPattern):
        pattern_name = "_instantiable_test"

        def execute(self, state, agent_registry, tool_registry):
            return state.to_run_result(output="executed")

    cls = PATTERN_REGISTRY["_instantiable_test"]
    instance = cls()
    assert isinstance(instance, BaseOrchestrationPattern)

    state = OrchestrationState(task="test", pattern="_instantiable_test")
    result = instance.execute(state, AgentRegistry(), ToolRegistry())
    assert result.status == "success"
    assert result.output == "executed"

    del PATTERN_REGISTRY["_instantiable_test"]


def test_abstract_pattern_cannot_be_instantiated():
    """BaseOrchestrationPattern itself is abstract and must not be instantiable."""
    # pytest.raises(...) is a context manager: the code inside the `with`
    # block must raise the given exception type, or the test fails. Here
    # there's no `match=...`, so it only checks the exception type (TypeError
    # — which is what Python's ABC machinery raises when you try to
    # instantiate a class that still has unimplemented @abstractmethods),
    # not its message.
    with pytest.raises(TypeError):
        BaseOrchestrationPattern()


def test_pattern_without_execute_raises_on_instantiate():
    """A subclass missing execute() should fail to instantiate."""
    class _IncompletePattern(BaseOrchestrationPattern):
        pattern_name = "_incomplete"
        # No execute() defined — abstract method still pending

    with pytest.raises(TypeError):
        _IncompletePattern()


# --- AgentRegistry ---

def test_agent_registry_register_and_get():
    from framework.agents.base import AgentConfig
    from framework.agents.concrete.stub import StubAgent

    registry = AgentRegistry()
    config = AgentConfig(id="researcher", role="researcher", system_prompt="You research things.")
    agent = StubAgent(config)
    registry.register(agent)

    retrieved = registry.get("researcher")
    # `is` checks identity, not equality — confirms registry.get() returned
    # the exact same StubAgent instance that was registered.
    assert retrieved is agent


def test_agent_registry_get_missing_raises_key_error():
    registry = AgentRegistry()
    with pytest.raises(KeyError, match="not in registry"):
        registry.get("ghost_agent")


def test_stub_agent_returns_agent_message():
    """StubAgent must return a valid AgentMessage, not raise."""
    from framework.agents.base import AgentConfig
    from framework.agents.concrete.stub import StubAgent
    from framework.agents.context import AgentContext
    from framework.orchestration.task import Task

    config = AgentConfig(id="stub", role="worker", system_prompt="stub")
    agent = StubAgent(config)

    task = Task(instruction="do something", agent_id="stub", parent_run_id="run-123")
    context = AgentContext(run_id="run-123", original_task="do something")

    message = agent.run(task, context)

    assert message.agent_id == "stub"
    assert message.role == "worker"
    assert isinstance(message.content, str)
    assert len(message.content) > 0
    assert message.metadata.get("stub") is True
