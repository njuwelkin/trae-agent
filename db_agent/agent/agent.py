from .session_manager import Conversation
from .pocketflow import AsyncFlow, AsyncNode
from db_agent.utils.output_stream import OutputStream, MessageType
from .prepare_node import GetToolsNode
from .call_llm_node import DecideNode
from .execute_tools_node import ExecuteToolsNode

class Agent:
    def __init__(self) -> None:
        # create_streaming_chat_flow here
        self.get_tool_node = GetToolsNode()
        self.decide_node = DecideNode()
        self.execute_node = ExecuteToolsNode()
        self.complete_node = CompleteNode()
        self.error_node = ErrorNode()
        
        self.get_tool_node - "call_llm" >> self.decide_node
        self.decide_node - "execute" >> self.execute_node
        self.decide_node - "call_llm" >> self.decide_node
        self.decide_node - "complete" >> self.complete_node
        self.execute_node - "call_llm" >> self.decide_node
        self.execute_node - "complete" >> self.complete_node

        self.get_tool_node - "error" >> self.error_node
        self.decide_node - "error" >> self.error_node
        self.execute_node - "error" >> self.error_node


    async def run(self, conversation: Conversation) -> None:
        # by default, run from start. if conversation.context["continue_on"] is set, continue from the setting node
        if conversation.context.get("is_continue", False):
            conversation.context['is_continue'] = True
            flow = AsyncFlow(self.execute_node)
        else:
            flow = AsyncFlow(self.get_tool_node)
        await flow.run_async(conversation.context)


class CompleteNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        # save chat to session
        session: Session = shared['session']
        #session.dump_chat_history()
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.start_chunk()
        await output_stream.send_text("Completed\n\n")
        await output_stream.end_chunk()
        return "done"

class ErrorNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.start_chunk()
        await output_stream.send_text("Completed\n\n")
        await output_stream.end_chunk()
        return "done"