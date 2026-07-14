# --------------------------------------------------------------------------
# This file's job: define what a "tool" IS (BaseTool — the contract concrete
# tools like tools/builtin/calculator.py implement) and provide the
# ToolRegistry that stores tool instances for a run and enforces per-agent
# permissions. Built by runtime/loader.py's _build_tool_registry() and handed
# to a Pattern's execute() (orchestration/patterns/base.py) alongside an
# AgentRegistry (agents/registry.py).
# --------------------------------------------------------------------------
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

    # `**kwargs` collects any extra keyword arguments a caller passes in beyond
    # `input`, into a dict named kwargs (e.g. calling run("2+2", foo="bar") puts
    # {"foo": "bar"} into kwargs). Declaring it here means every tool's run()
    # signature can accept extra parameters without every implementation having
    # to redeclare them — it's a flexible "catch-all" for future/tool-specific
    # options that the base class doesn't need to know about in advance.
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

    Why a registry instead of passing tool instances around directly: the same
    reasoning as AgentRegistry (agents/registry.py) — a workflow's tool list is
    built dynamically from YAML, and callers need to look a tool up by name
    string at run time. On top of that lookup role, ToolRegistry adds a second
    job registries alone don't need: gatekeeping. invoke() is the only method
    that checks an agent's allowed_tools before running anything, so routing
    every tool call through the registry (never through a raw tool.run() call)
    is what makes per-agent tool permissions actually enforceable.
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

        Why invoke() is the ONLY correct way to call a tool: `tool.run(input)`
        is a completely ordinary method call — nothing on BaseTool or its
        subclasses stops any code, anywhere, from calling it directly. The
        permission check (is this agent allowed to use this tool?) lives
        entirely in this method, not in the tool itself. So if agent or
        pattern code ever calls `some_tool.run(...)` directly instead of going
        through `tool_registry.invoke(...)`, it silently skips the
        allowed_tools check above and lets an agent use a tool it was never
        granted — the permission system only works if every call path goes
        through here.
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
        # A list comprehension can have a trailing `if` clause that *filters*
        # which items make it into the result — this reads as "for each name in
        # allowed_tools, but only keep it if name is also in self._tools, and
        # for the ones that pass, put self._tools[name].to_schema() in the
        # list." It's equivalent to a for-loop with an `if: continue` guard,
        # but expressed as a single filtering-and-transforming expression.
        return [
            self._tools[name].to_schema()
            for name in allowed_tools
            if name in self._tools
        ]

    def registered_names(self) -> list[str]:
        return list(self._tools.keys())

    # See AgentRegistry.__len__/__repr__ in agents/registry.py for what these
    # "dunder" methods do — same idea here: len(tool_registry) and
    # print(tool_registry) work out of the box because of these.
    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.registered_names()!r}>"
