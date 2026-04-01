"""Live tool registry — builds the complete set of executable tools."""
from __future__ import annotations
from ..permissions import ToolPermissionContext
from .base import BaseTool
from .read_tool import ReadTool
from .write_tool import WriteTool
from .edit_tool import EditTool
from .bash_tool import BashTool
from .grep_tool import GrepTool
from .glob_tool import GlobTool
from .agent_tool import AgentTool


def build_live_tool_registry(
    llm_client=None,  # BaseLLMClient | None
    permission_context: ToolPermissionContext | None = None,
    hook_registry=None,  # HookRegistry | None
    exclude_tools: frozenset[str] = frozenset(),
) -> dict[str, BaseTool]:
    """Build a complete tool registry with real implementations.

    Args:
        llm_client: LLM client for the Agent tool to use for sub-spawning.
        permission_context: Permission deny lists. Blocked tools are excluded.
        hook_registry: Hook registry for the Agent tool's sub-agents.
        exclude_tools: Tool names to explicitly exclude (e.g. {'Agent'} for sub-agents).
    """
    tools: dict[str, BaseTool] = {}

    # Core file tools
    tools['Read'] = ReadTool()
    tools['Write'] = WriteTool()
    tools['Edit'] = EditTool()

    # Shell tools
    tools['Bash'] = BashTool()
    tools['Grep'] = GrepTool()
    tools['Glob'] = GlobTool()

    # Agent tool — only if LLM client provided and not excluded
    if llm_client is not None and 'Agent' not in exclude_tools:
        def tool_factory() -> dict[str, BaseTool]:
            """Factory for sub-agent tools — excludes Agent to prevent recursion."""
            return build_live_tool_registry(
                llm_client=llm_client,
                permission_context=permission_context,
                hook_registry=hook_registry,
                exclude_tools=frozenset({'Agent'}),
            )

        tools['Agent'] = AgentTool(
            llm_client=llm_client,
            tool_registry_factory=tool_factory,
            hook_registry=hook_registry,
        )

    # Apply permission filtering
    if permission_context:
        tools = {name: tool for name, tool in tools.items()
                 if not permission_context.blocks(name)}

    # Apply explicit exclusions
    if exclude_tools:
        tools = {name: tool for name, tool in tools.items()
                 if name not in exclude_tools}

    return tools
