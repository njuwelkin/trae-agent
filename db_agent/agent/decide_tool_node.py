from .pocketflow import AsyncNode
from db_agent.utils.output_stream import OutputStream
from db_agent.utils.llm_basics import LLMMessage, LLMResponse
from .call_llm_node import CallLLMNode
import time

class DecideNode(AsyncNode):
    def __init__(self) -> None:
        super().__init__()
        self.base = CallLLMNode()

    async def prep_async(self, shared):
        """Initialize and get tools"""
        return await self.base.prep_async(shared)

    async def exec_async(self, prep_res):
        """Retrieve tools from the MCP server"""
        return await self.base.exec_async(prep_res, log_to_history=True)

    async def post_async(self, shared, prep_res, exec_res):
        """Store tools and process to decision node"""
        llm_response, error = exec_res
        if error:
            shared["error"] = error
            return "error"

        output_stream : OutputStream = shared["output_stream"]

        llm_response: LLMResponse = llm_response
        if len(llm_response.content) > 0:
            shared['chat_history'].append(
                #LLMMessage(role="assistant", content=llm_response.content)
                {"role": "assistant", "content": llm_response.content}
            )
            await output_stream.send_chunk(llm_response.content)
            shared['answer'].append(llm_response.content)

        if llm_response.finish_reason == "stop" and (llm_response.tool_calls is None or len(llm_response.tool_calls) == 0):
            if len(llm_response.content) > 0:
                #shared["next_messages"] = [
                #    LLMMessage(
                #        role="user", 
                #        content="If you think task is completed, call `task_done` to finish the conversation."
                #    )
                #]
                # return "call_llm"
                # directly return, to save time
                return "complete"
            else:
                shared["next_messages"] = [
                    LLMMessage(
                        role="user", 
                        content="It seems that you have not completed the task. You should return result to user."
                    )
                ]
                return "call_llm"
        else:  # if self.llm_indicates_task_completed
            tool_calls = llm_response.tool_calls
            shared["tool_calls"] = tool_calls
            return "execute"

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