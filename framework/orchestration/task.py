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
    """
    instruction: str
    agent_id: str
    parent_run_id: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context_snapshot: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
