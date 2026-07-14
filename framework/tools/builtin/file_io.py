# --------------------------------------------------------------------------
# This file's job: two concrete BaseTool (tools/base.py) implementations that
# let an agent read/write files on disk, constrained to a whitelist of
# allowed directories. Registered by runtime/loader.py's _TOOL_CLASSES map
# under "file_read"/"file_write" and instantiated into a ToolRegistry
# (tools/base.py) at workflow-build time.
# --------------------------------------------------------------------------
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

    # Security check: an agent could be given a path like "../../etc/passwd" or
    # some other traversal outside the intended directory. os.path.abspath()
    # resolves the given path to a full, normalized absolute path (collapsing
    # any ".." segments), and then str.startswith() checks whether that
    # resolved path actually lives inside one of the resolved allowed_paths
    # directories. Doing the comparison on abspath() output (both sides) — not
    # on the raw strings — is what prevents "./artifacts/../../secrets"-style
    # tricks from slipping past a naive string check.
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

    # Same allowed-directory check as FileReadTool._is_allowed above — see that
    # method's comment for why abspath()+startswith() is used.
    def _is_allowed(self, path: str) -> bool:
        return any(os.path.abspath(path).startswith(p) for p in self.allowed_paths)

    def run(self, input: str, **kwargs) -> str:
        if "|||" not in input:
            return "Error: input must be 'filepath|||content'. Separator ||| not found."
        # str.split(sep, maxsplit) — the `1` caps how many splits happen: split
        # on the FIRST "|||" only, and leave everything after it (even if it
        # contains more "|||" sequences) intact as the second piece. Without
        # the `1`, content that itself happens to contain "|||" would get
        # chopped into more than two pieces and this unpacking
        # (`path, content = ...`) would raise a ValueError ("too many values to
        # unpack") instead of cleanly separating "path" from "everything else".
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
