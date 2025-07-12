from .pocketflow import AsyncNode
from db_agent.utils.output_stream import OutputStream
from db_agent.utils.llm_basics import LLMMessage, LLMResponse
from .call_llm_node import CallLLMNode

class ExplainNode(AsyncNode):
    def __init__(self) -> None:
        super().__init__()
        self.base = CallLLMNode()

    async def prep_async(self, shared):
        """Initialize and get tools"""
        shared["next_messages"] = [
            LLMMessage(
                role="user",
                content="""Explain the tools you selected in previous step.
The purpose of using these tools. The name of each tool and the description of each tool.
As an example:
---
We need to get the user_id of 'Alice' and query the cars associated with the uid.
Step 1: use the 'exec_sql' tool with 'select user_id from user where name = 'Alice''.
Step 2: use the 'exec_sql' tool with 'select * from car where uid = <user_id>'.
---
""",
            )
        ]
        return await self.base.prep_async(shared)

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return await self.base.exec_async(prep_res, log_to_history=False)

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        llm_response, error = exec_res
        if error:
            shared["error"] = error
            # ignore the error of this step, as it's not necessary
            return "execute"

        output_stream : OutputStream = shared["output_stream"]

        llm_response: LLMResponse = llm_response
        if len(llm_response.content) > 0:
            shared['chat_history'].append(
                #LLMMessage(role="assistant", content=llm_response.content)
                {"role": "assistant", "content": llm_response.content}
            )
            await output_stream.send_chunk(llm_response.content)

        return "execute"