import os
from ..base import BaseTool


class FileReadTool(BaseTool):
    """Read the text contents of a file. Restricted to allowed paths."""
    name = "file_read"
    description = (
        "Read the text content of a file. "
        "Input should be the file path relative to the project root."
    )

    def __init__(self, allowed_paths: list[str] | None = None):
        self.allowed_paths = [os.path.abspath(p) for p in (allowed_paths or ["./artifacts"])]

    def _is_allowed(self, path: str) -> bool:
        return any(os.path.abspath(path).startswith(p) for p in self.allowed_paths)

    def run(self, input: str, **kwargs) -> str:
        path = input.strip()
        if not self._is_allowed(path):
            return f"Error: '{path}' is outside allowed directories."
        if not os.path.exists(path):
            return f"Error: file '{path}' does not exist."
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"


class FileWriteTool(BaseTool):
    """
    Write text content to a file. Restricted to allowed paths.
    Input format: 'path/to/file.txt|||content to write'
    The ||| separator splits the path from the content.
    """
    name = "file_write"
    description = (
        "Write text content to a file. "
        "Input format: 'filepath|||content'. "
        "Example: 'artifacts/report.md|||# Report\\nContent here'"
    )

    def __init__(self, allowed_paths: list[str] | None = None):
        self.allowed_paths = [os.path.abspath(p) for p in (allowed_paths or ["./artifacts"])]

    def _is_allowed(self, path: str) -> bool:
        return any(os.path.abspath(path).startswith(p) for p in self.allowed_paths)

    def run(self, input: str, **kwargs) -> str:
        if "|||" not in input:
            return "Error: input must be 'filepath|||content'. Separator ||| not found."
        path, content = input.split("|||", 1)
        path = path.strip()
        if not self._is_allowed(path):
            return f"Error: '{path}' is outside allowed directories."
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Wrote {len(content)} characters to '{path}'."
        except Exception as e:
            return f"Error writing file: {e}"
