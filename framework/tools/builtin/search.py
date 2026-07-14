# --------------------------------------------------------------------------
# This file's job: a placeholder BaseTool (tools/base.py) implementation
# standing in for a real web-search provider, so workflows can be built and
# tested end-to-end before one is wired up. Registered by runtime/loader.py's
# _TOOL_CLASSES map under the "search" type.
# --------------------------------------------------------------------------
from ..base import BaseTool


class MockSearchTool(BaseTool):
    """
    Mock web search for development and testing.
    Returns a canned response instead of hitting a real search API.
    Swap this out for a real provider (Serper, Tavily, SerpAPI) when ready.
    """
    name = "web_search"
    description = (
        "Search the web for current information on a topic. "
        "Use when you need facts, recent events, or data you don't have."
    )

    def run(self, input: str, **kwargs) -> str:
        return (
            f"[MOCK SEARCH RESULT for: '{input}']\n"
            f"Placeholder result. Replace MockSearchTool with a real provider."
        )
