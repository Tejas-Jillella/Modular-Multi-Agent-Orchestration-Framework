# --------------------------------------------------------------------------
# This file's job: a cross-agent key/value store for one run, meant as a more
# structured alternative to stuffing everything into
# OrchestrationState.message_history (orchestration/state.py). NOT currently
# instantiated or used anywhere in the pipeline — like memory/local.py and
# memory/artifacts.py, it's a more capable version of an idea
# OrchestrationState already handles in a simpler way today, waiting to be
# wired in during Goal 10.
# --------------------------------------------------------------------------
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SharedWorkflowMemory:
    """
    Key-value store shared across all agents in a single run.
    In-memory only — does not persist after the run ends.

    Use for: passing facts, intermediate summaries, flags between agents
    without going through OrchestrationState's message_history.
    """
    run_id: str
    store: dict[str, Any] = field(default_factory=dict)

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self.store

    def keys(self) -> list[str]:
        return list(self.store.keys())

    def clear(self) -> None:
        self.store.clear()
