from mcp.types import Tool as MCPTool
from db_agent.tools import Tool as LocalTool
from db_agent.utils.llm_client import LLMClient
from db_agent.utils.output_stream import OutputStream
from db_agent.utils.llm_basics import LLMMessage
from .chunk_printer import ChunkPrinter

class CallLLMNode():
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.update_status("Thinking")

        local_tools = shared["local_tools"]
        mcp_tools = shared["mcp_tools"]
        llm_client = shared["llm_client"]
        messages = shared["next_messages"]
        output_stream = shared["output_stream"]
        return llm_client, local_tools, mcp_tools, messages, output_stream

    async def exec_async(self, prep_res, log_to_history):
        """Retrieve tools from the MCP server"""
        llm_client, local_tools, mcp_tools, messages, output_stream = prep_res

        llm_client: LLMClient = llm_client
        local_tools: list[LocalTool] = local_tools
        mcp_tools: list[MCPTool] = mcp_tools
        messages: list[LLMMessage] = messages
        output_stream: OutputStream = output_stream

        print(messages)
        chunk_printer = ChunkPrinter(output_stream)
        try:
            llm_response = await llm_client.a_chat(
                #messages, local_tools, mcp_tools, log_to_history
                messages=messages,
                local_tools=local_tools,
                mcp_tools=mcp_tools,
                log_to_history=log_to_history,
                printer=chunk_printer,
            )
        except Exception as e:
            print(f"Error in LLM chat: {e}")
            if chunk_printer.started:
                await output_stream.end_chunk()
            return None, e
            
        if chunk_printer.started:
            await output_stream.end_chunk()
        return llm_response, None

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        pass