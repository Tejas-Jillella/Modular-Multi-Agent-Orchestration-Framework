"""
Modular Multi-Agent Orchestration Framework

Package entrypoint. This is what `import framework` actually gives you.
It re-exports the two functions callers need (run_workflow, load_workflow_config)
from runtime/loader.py, so cli.py and external code can do
`from framework import run_workflow` instead of reaching into the submodule path.
"""
# The leading dot means "from this same package" — .runtime.loader refers to
# framework/runtime/loader.py, resolved relative to this file's location rather
# than searching sys.path for a top-level module named "runtime".
from .runtime.loader import run_workflow, load_workflow_config

__version__ = "0.1.0"
# __all__ tells `from framework import *` which names to expose; it also documents
# the intended public API of this package for anyone browsing the source.
__all__ = ["run_workflow", "load_workflow_config"]
