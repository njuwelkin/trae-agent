from mcp.types import Tool as MCPTool
from db_agent.tools import Tool as LocalTool
from db_agent.tools import ToolExecutor, ToolResult
from .pocketflow import AsyncNode
from db_agent.utils.output_stream import OutputStream
from db_agent.tools import ToolCall
from db_agent.utils.llm_basics import LLMMessage, LLMResponse

class ExecuteToolsNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.update_status("Executing")

        tool_calls: list[ToolCall] = shared["tool_calls"]
        self.tool_caller = ToolExecutor(shared["local_tools"])
        return tool_calls

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        tool_calls: list[ToolCall] = prep_res

        for call in tool_calls:
            results: list[ToolResult] = []
            if call.name in ["sequentialthinking", "task_done"]:
                results.append(self.exec_local_tool(call))
            else:
                results.append(self.exec_mcp_tool(call))
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "check"

    def exec_local_tool(self, tool_call: ToolCall):
        pass

    async def exec_mcp_tool(self, tool_call: ToolCall):
        return await self.tool_caller.execute_tool_call(tool_call)
        