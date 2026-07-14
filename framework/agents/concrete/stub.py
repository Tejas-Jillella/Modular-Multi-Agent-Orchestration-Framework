# --------------------------------------------------------------------------
# This file's job: provide the one CONCRETE agent that exists today, so the
# rest of the pipeline (loader -> pattern -> agent -> result) can be built and
# tested before any real LLM-backed agent exists. runtime/loader.py currently
# wraps every AgentConfig in a StubAgent; future goals will add real agent
# classes here alongside (or in place of) this one.
# --------------------------------------------------------------------------
# The leading dots are Python's *relative import* syntax: each dot walks up one
# package level from this file's location (framework/agents/concrete/stub.py).
# One dot (`.`) means "this same package" (agents/concrete/), two dots (`..`)
# means "one level up" (agents/), three dots (`...`) means "two levels up"
# (framework/). So `from ..base import ...` reaches agents/base.py, and
# `from ...orchestration.task import ...` reaches framework/orchestration/task.py.
from ..base import BaseAgent, AgentConfig
from ..context import AgentContext
from ...orchestration.task import Task, AgentMessage


class StubAgent(BaseAgent):
    """
    Placeholder agent for Goal 3 skeleton testing.

    Returns a clearly-labelled stub response so the full pipeline
    (loader -> pattern -> agent -> result) can be tested end-to-end
    without a real LLM connection. Replaced by concrete agents in Goals 4-9.
    """

    # BaseAgent (agents/base.py) is an ABC with run() marked @abstractmethod,
    # which means BaseAgent itself can't be instantiated — Python blocks it.
    # Defining a concrete run() method here is exactly what "un-blocks"
    # instantiation: because StubAgent supplies every abstract method BaseAgent
    # requires, `StubAgent(config)` is now legal where `BaseAgent(config)` was not.
    def run(self, task: Task, context: AgentContext) -> AgentMessage:
        return AgentMessage(
            agent_id=self.id,
            role=self.role,
            content=(
                f"[STUB] Agent '{self.id}' received task:\n"
                f"{task.instruction}\n\n"
                f"Replace StubAgent with a concrete agent class to get real output."
            ),
            metadata={"stub": True},
        )
