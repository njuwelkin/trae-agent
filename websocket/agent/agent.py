from .session_manager import Conversation
from .pocketflow import AsyncFlow, AsyncNode
from websocket.utils.output_stream import OutputStream, MessageType

class Agent:
    def __init__(self) -> None:
        # create_streaming_chat_flow here
        self.get_tool_node = GetToolsNode()
        self.decide_node = DecideToolsNode()
        self.execute_node = ExecuteToolsNode()
        self.check_result_node = CheckResultNode()
        self.complete_node = CompleteNode()
        
        self.get_tool_node - "decide" >> self.decide_node
        self.decide_node - "execute" >> self.execute_node
        self.execute_node - "check" >> self.check_result_node
        self.check_result_node - "continue" >> self.complete_node
        self.check_result_node - "complete" >> self.complete_node

        self.get_tool_node - "error" >> self.complete_node
        self.decide_node - "error" >> self.complete_node
        self.execute_node - "error" >> self.complete_node
        self.check_result_node - "error" >> self.complete_node


    async def run(self, conversation: Conversation) -> None:
        # by default, run from start. if conversation.context["continue_on"] is set, continue from the setting node
        if conversation.context.get("continue_on"):
            flow = AsyncFlow(conversation.context["continue_on"])
        else:
            flow = AsyncFlow(self.get_tool_node)
        await flow.run_async(conversation.context)



class GetToolsNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.update_status(MessageType.START)
        #await output_stream.send_text("Retrieving tools...\n\n")
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "decide"


class DecideToolsNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.send_text("decide tools")
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "execute"


class ExecuteToolsNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.send_text("Execute tools...")
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "check"

class CheckResultNode(AsyncNode): # maybe reflect node, check result is done in post of execute
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.send_text("reflect...")
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "complete"

class CompleteNode(AsyncNode):
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        await output_stream.send_text("Complete...")
        await output_stream.update_status(MessageType.END)
        return ""

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return "tools"

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        return "done"