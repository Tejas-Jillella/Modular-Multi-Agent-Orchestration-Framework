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
