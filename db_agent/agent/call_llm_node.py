from mcp.types import Tool as MCPTool
from db_agent.tools import Tool as LocalTool
from db_agent.utils.llm_client import LLMClient
from .pocketflow import AsyncNode
from db_agent.utils.output_stream import OutputStream
from db_agent.utils.llm_basics import LLMMessage, LLMResponse

class DecideNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.update_status("Thinking")

        local_tools = shared["local_tools"]
        mcp_tools = shared["mcp_tools"]
        llm_client = shared["llm_client"]
        messages = shared["next_messages"]
        return llm_client, local_tools, mcp_tools, messages

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        llm_client, local_tools, mcp_tools, messages = prep_res

        llm_client: LLMClient = llm_client
        local_tools: list[LocalTool] = local_tools
        mcp_tools: list[MCPTool] = mcp_tools
        messages: list[LLMMessage] = messages

        try:
            llm_response = await llm_client.a_chat(
                messages, local_tools, mcp_tools
            )
        except Exception as e:
            print(f"Error in LLM chat: {e}")
            return None, e
        return llm_response, None

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        llm_response, error = exec_res
        if error:
            shared["error"] = e
            return "error"

        output_stream : OutputStream = shared["output_stream"]

        llm_response: LLMResponse = llm_response
        if len(llm_response.content) > 0:
            shared['chat_history'].append(
                #LLMMessage(role="assistant", content=llm_response.content)
                {"role": "assistant", "content": llm_response.content}
            )
            await output_stream.send_chunk(llm_response.content)

        if self.llm_indicates_task_completed(llm_response):
            if self.is_task_completed(llm_response):
                return "complete"
            else:
                shared["next_messages"] = [
                    LLMMessage(
                        role="user", 
                        content="#tell llm task is incomplete and the reason"
                    )
                ]
                return "call_llm"
        else:  # if self.llm_indicates_task_completed
            tool_calls = llm_response.tool_calls
            if tool_calls and len(tool_calls) > 0:
                shared["tool_calls"] = tool_calls
                return "execute"
            else:
                shared["next_messages"] = [
                    LLMMessage(
                        role="user",
                        content="It seems that you have not completed the task.",
                    )
                ]
                return "call_llm"

    def llm_indicates_task_completed(self, llm_response: LLMResponse) -> bool:
        """Check if the LLM indicates that the task is completed. Override for custom logic."""
        completion_indicators = [
            "task completed",
            "task finished",
            "done",
            "completed successfully",
            "finished successfully",
        ]

        response_lower = llm_response.content.lower()
        return any(indicator in response_lower for indicator in completion_indicators)
    
    def is_task_completed(self, llm_response: LLMResponse) -> bool:  # pyright: ignore[reportUnusedParameter]
        """Check if the task is completed based on the response."""
        return True