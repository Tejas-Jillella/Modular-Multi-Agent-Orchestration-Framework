from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    A tool is any capability an agent can invoke during its LLM loop.
    Every tool must have a name (registry key), description (shown to the LLM),
    and a run() method that returns a plain string.
    """

    name: str         # must match the string in AgentConfig.allowed_tools
    description: str  # shown to the LLM so it knows when to call this tool

    @abstractmethod
    def run(self, input: str, **kwargs) -> str:
        """Execute the tool. Always returns a plain string."""
        raise NotImplementedError

    def to_schema(self) -> dict:
        """
        Build the function-calling schema for this tool.
        This is the exact JSON format the OpenAI-compatible vLLM API
        expects in the 'tools' field of a chat completions request.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema(),
            }
        }

    def input_schema(self) -> dict:
        """
        JSON Schema describing this tool's input parameters.
        Override in subclasses that take more than one plain string input.
        """
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "The input for this tool"}
            },
            "required": ["input"],
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"


class ToolRegistry:
    """
    Stores all available tools and enforces per-agent permissions.

    ALL tool calls must go through invoke() — never call tool.run() directly
    from agent or pattern code, because that bypasses permission checks.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Add a tool to the registry."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        """Retrieve a tool by name. Raises KeyError if not registered."""
        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' not in registry. Registered: {list(self._tools.keys())}"
            )
        return self._tools[name]

    def invoke(self, name: str, input: str, agent_id: str, allowed_tools: list[str]) -> str:
        """
        Execute a tool with permission enforcement.

        Order of checks (fail fast):
        1. Is this tool in the agent's allowed_tools list?
        2. Is this tool registered?
        Only if both pass does it call tool.run(input).

        This is the runtime enforcement point for Goal 11 (tool permissions).
        Config-load checks alone are not sufficient — they can be bypassed
        by a misconfigured or prompt-injected agent.
        """
        if name not in allowed_tools:
            raise PermissionError(
                f"Agent '{agent_id}' is not allowed to use tool '{name}'. "
                f"Allowed tools: {allowed_tools}"
            )
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered.")
        return self._tools[name].run(input)

    def get_schemas_for_agent(self, allowed_tools: list[str]) -> list[dict]:
        """
        Build the tools list to include in an LLM API call.
        Only includes tools the agent is allowed to use AND that are registered.
        """
        return [
            self._tools[name].to_schema()
            for name in allowed_tools
            if name in self._tools
        ]

    def registered_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.registered_names()!r}>"
