import json
from db_agent.tools import ToolExecutor, ToolResult
from .pocketflow import AsyncNode
from db_agent.utils.output_stream import OutputStream
from db_agent.tools import ToolCall
from db_agent.utils.mcp_client import MCPClientBase
from fastmcp.client.client import CallToolResult
from db_agent.utils.llm_client import LLMMessage

class ExecuteToolsNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.update_status("Executing")

        tool_calls: list[ToolCall] = shared["tool_calls"]
        self.tool_caller = ToolExecutor(shared["local_tools"])

        self.mcp_client: MCPClientBase = shared["mcp_client"]
        return tool_calls

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        tool_calls: list[ToolCall] = prep_res

        results: list[ToolResult] = []
        for call in tool_calls:
            if call.name in ["sequentialthinking", "task_done", "chat_history"]:
                results.append(await self.exec_local_tool(call))
            else:
                if self.mcp_client is not None:
                    results.append(await self.exec_mcp_tool(call))
        return results

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        if "task_done" in shared and shared["task_done"]:
            return "complete"

        results : list[ToolResult] = exec_res

        shared["next_messages"] = []
        for result in results:
            message = LLMMessage(
                role="user", tool_result=result
            )
            shared["next_messages"].append(message)
       
        #reflection = self.reflect_on_result(results)
        #if reflection:
        #    shared["next_messages"].append(LLMMessage(
        #        role="assistant", content=reflection
        #    ))
        
        return "call_llm"

    async def exec_local_tool(self, tool_call: ToolCall) -> ToolResult:
        return await self.tool_caller.execute_tool_call(tool_call)
        
    async def exec_mcp_tool(self, tool_call: ToolCall):
        try:
            async with self.mcp_client as client:
                result: CallToolResult = await client.call_tool(
                    tool_name=tool_call.name,
                    parameters=tool_call.arguments
                )
            return ToolResult(
                id=tool_call.id,
                call_id=tool_call.call_id,
                name=tool_call.name,
                result=result.content if not result.is_error else "",
                success=not result.is_error,
                error=None if not result.is_error else result.content
            )
        except Exception as e:
            return ToolResult(
                id=tool_call.id,
                call_id=tool_call.call_id,
                name=tool_call.name,
                result="",
                success=False,
                error=str(e)
            )

    def reflect_on_result(self, tool_results: list[ToolResult]) -> str | None:
        """Reflect on tool execution result. Override for custom reflection logic."""
        if len(tool_results) == 0:
            return None

        reflection = "\n".join(
            f"The tool execution failed with error: {tool_result.error}. Consider trying a different approach or fixing the parameters."
            for tool_result in tool_results
            if not tool_result.success
        )

        return reflection