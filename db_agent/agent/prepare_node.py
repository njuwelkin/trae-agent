from .pocketflow import AsyncNode
from db_agent.utils.mcp_client import MCPClientBase
from db_agent.tools import TaskDoneTool, SequentialThinkingTool, ChatHistoryTool
from db_agent.tools import Tool as LocalTool
from db_agent.utils.output_stream import OutputStream
from mcp.types import Tool as MCPTool
from db_agent.utils.llm_basics import LLMMessage
from db_agent.tools import ToolExecutor
from .prompt import *

class PrepareNode(AsyncNode):
    """ 
        Choose MCP server according to user message .
        Get Tools from MCP server.
        Get Local Tools.
        Prepare every thing
    """
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        output_stream.update_status("Getting tools")

        mcp_client = shared["mcp_client"]
        shared['chat_history'] = [
            #LLMMessage(role="user", content=shared["user_message"]),
            {"role": "user", "content": shared["user_message"]}
        ]
        shared['task_done'] = False
        shared['answer']: list[str] = []
        return mcp_client

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        mcp_client: MCPClientBase = prep_res
        if mcp_client is None:
            return [], None

        try:
            async with mcp_client:
                tools = await mcp_client.list_tools()
        except Exception as e:
            print(e)
            return None, e
        return tools, None

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        mcp_tools, error = exec_res
        if error is not None:
            shared["error"] = error
            return "error"

        mcp_tools: list[MCPTool] = mcp_tools
        shared['mcp_tools'] = mcp_tools
        print([tool.name for tool in mcp_tools])

        session = shared['session']
        # TODO: get provider from llm_client
        #provider = self.llm_client.provider.value
        provider = "deepseek"
        #local_tools: list[LocalTool] = [
        #    tools_registry[tool_name](model_provider=provider)
        #    for tool_name in ["sequentialthinking", "task_done"]
#]
        local_tools: list[LocalTool] = []
        local_tools.append(SequentialThinkingTool(model_provider=provider))
        local_tools.append(TaskDoneTool(model_provider=provider, 
            can_complete=lambda: len(shared["answer"]) > 0,
            set_complete=lambda: shared.update({"task_done": True}),
            incomplete_prompt="It seems that you have not completed the task. You should return result to user.",
        ))
        local_tools.append(ChatHistoryTool(model_provider=provider, call_back=session.dump_chat_history))
        shared['local_tools'] = local_tools
        tool_caller: ToolExecutor = ToolExecutor(local_tools)
        shared['tool_caller'] = tool_caller
        print(local_tools)

        shared['next_messages'] = [
            LLMMessage(role="system", content=self.get_system_prompt()),
            LLMMessage(role="user", content=shared["user_message"]),
        ]
        return "call_llm"

    def get_system_prompt(self) -> str:
        """Get the system prompt for TraeAgent."""
        return DBA_PROMPT