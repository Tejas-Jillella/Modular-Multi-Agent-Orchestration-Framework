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
