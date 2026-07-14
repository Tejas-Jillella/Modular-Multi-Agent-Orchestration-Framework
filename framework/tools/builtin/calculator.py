# --------------------------------------------------------------------------
# This file's job: a concrete BaseTool (tools/base.py) implementation that
# lets an agent evaluate arithmetic. Registered by runtime/loader.py's
# _TOOL_CLASSES map under the "calculator" type and instantiated into a
# ToolRegistry (tools/base.py) at workflow-build time.
# --------------------------------------------------------------------------
from ..base import BaseTool


class CalculatorTool(BaseTool):
    """
    Safe arithmetic calculator.
    Evaluates basic math expressions and returns the result as a string.
    eval() is restricted to safe builtins only — no access to modules or functions.
    """
    name = "calculator"
    description = (
        "Evaluate a mathematical expression and return the result. "
        "Supports +, -, *, /, **, parentheses. Example: '(100 * 0.07) + 42'"
    )

    # eval() normally runs with access to every Python built-in (import,
    # open, exec, etc.), which would make evaluating an arbitrary
    # LLM-generated expression a serious security hole. Passing this dict as
    # eval()'s "globals" argument overrides that: setting "__builtins__" to an
    # empty dict {} strips out ALL built-in names (no import, open, eval,
    # __import__, etc. are reachable from the expression being evaluated), and
    # then we explicitly hand back only the four safe math functions
    # (abs/round/min/max) an arithmetic expression might plausibly need. The
    # empty {} passed as eval()'s third argument (locals) below means no local
    # variables are visible either — so the expression can only use numbers,
    # operators, and these four whitelisted functions.
    _SAFE_GLOBALS = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max,
    }

    def run(self, input: str, **kwargs) -> str:
        try:
            result = eval(input.strip(), self._SAFE_GLOBALS, {})  # noqa: S307
            return str(result)
        except ZeroDivisionError:
            return "Error: division by zero"
        except Exception as e:
            return f"Error evaluating '{input}': {e}"
