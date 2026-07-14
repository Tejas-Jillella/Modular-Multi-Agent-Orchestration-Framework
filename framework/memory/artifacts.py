# --------------------------------------------------------------------------
# This file's job: a disk-backed store for named artifacts (reports,
# generated files) that survive after a run ends, unlike everything else in
# framework/memory/ and OrchestrationState.artifacts (orchestration/state.py),
# which are in-memory only. NOT currently instantiated or used anywhere in
# the pipeline — OrchestrationState.save_artifact() currently just keeps
# artifact content in a plain in-memory dict for the duration of the run.
# ArtifactStore is the more capable, persistent version of that same idea,
# meant to be wired in during Goal 10.
# --------------------------------------------------------------------------
import os
from dataclasses import dataclass


@dataclass
class ArtifactStore:
    """
    Named file outputs produced by agents. Backed by local files.
    Survives after the run ends — the only memory layer that does.

    Use for: reports, generated code, data files — anything that needs
    to persist beyond the run or be shared between agents.
    """
    run_id: str
    artifact_dir: str = "./artifacts"

    def save(self, name: str, content: str) -> str:
        """Write content to a named artifact. Returns the file path."""
        os.makedirs(self.artifact_dir, exist_ok=True)
        path = os.path.join(self.artifact_dir, f"{self.run_id}_{name}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def load(self, name: str) -> str:
        """Read a named artifact back as a string."""
        path = os.path.join(self.artifact_dir, f"{self.run_id}_{name}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Artifact '{name}' not found for run '{self.run_id}'")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def exists(self, name: str) -> bool:
        return os.path.exists(os.path.join(self.artifact_dir, f"{self.run_id}_{name}"))

    def list(self) -> list[str]:
        """List all artifact names for this run (without the run_id prefix)."""
        if not os.path.exists(self.artifact_dir):
            return []
        prefix = f"{self.run_id}_"
        # List comprehension with a trailing filter `if`: for each filename in
        # the artifact directory, keep it only if it starts with this run's
        # prefix, and for the ones kept, strip that prefix off before adding it
        # to the result list. Equivalent to a for-loop with an `if` guard, but
        # written as one expression.
        return [
            f.replace(prefix, "", 1)
            for f in os.listdir(self.artifact_dir)
            if f.startswith(prefix)
        ]

    def delete(self, name: str) -> None:
        path = os.path.join(self.artifact_dir, f"{self.run_id}_{name}")
        if os.path.exists(path):
            os.remove(path)
