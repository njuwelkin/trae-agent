"""OpenAI API client wrapper with tool integration."""

import json
import os
import random
import time
from typing import override, AsyncGenerator

import openai

from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionToolMessageParam,
    ChatCompletionChunk,
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)
from openai.types.chat.chat_completion import Choice    

from openai.types.shared_params import FunctionDefinition
from mcp.types import Tool as MCPTool

from db_agent.tools.base import Tool, ToolCall, ToolResult
from .config import ModelParameters
from .base_client import BaseLLMClient
from .llm_basics import LLMMessage, LLMResponse, LLMUsage


class AsyncOpenAIClient():
    """OpenAI client wrapper with tool schema generation."""

    def __init__(self, model_parameters: ModelParameters):
        self.provider = "deepseek"
        self.model_parameters: ModelParameters = model_parameters

        self.api_key: str = os.getenv("OPENAI_API_KEY", "")

        if self.api_key == "":
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY in environment variables or config file."
            )

        self.client: openai.AsyncOpenAI = openai.AsyncOpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        self.message_history: list[ChatCompletionMessageParam] = []
        self.model_parameters: ModelParameters = model_parameters

    @override
    def set_chat_history(self, messages: list[LLMMessage]) -> None:
        """Set the chat history."""
        self.message_history = self.parse_messages(messages)

 
    @override
    async def a_chat(
        self,
        messages: list[LLMMessage],
        #model_parameters: ModelParameters,
        local_tools: list[Tool] | None = None,
        mcp_tools: list[MCPTool] | None = None,
        reuse_history: bool = True,
        log_to_history: bool = True,
    ) -> LLMResponse:
        """Send chat messages to OpenAI with optional tool support."""
        model_parameters: ModelParameters = self.model_parameters
        openai_messages: list[ChatCompletionMessageParam] = self.parse_messages(messages)

        tool_schemas = None
        if local_tools:
            tool_schemas = [
                ChatCompletionToolParam(
                    type="function",
                    function=FunctionDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.get_input_schema(),
                        strict=True
                    )
                )
                for tool in local_tools
            ]
        if mcp_tools:
            tool_schemas.extend([
                ChatCompletionToolParam(
                    type="function",
                    function=FunctionDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.inputSchema,
                        strict=True
                    )
                )
                for tool in mcp_tools
            ])

        api_call_input: list[ChatCompletionMessageParam] = []
        if reuse_history:
            api_call_input.extend(self.message_history)
        api_call_input.extend(openai_messages)

        response = None
        error_message = ""
        for i in range(model_parameters.max_retries):
            try:
                response = await self.get_full_completion_stream(
                    messages=api_call_input,
                    tools=tool_schemas,
                    model_parameters=model_parameters
                )
                break
            except Exception as e:
                error_message += f"Error {i + 1}: {str(e)}\n"
                # Randomly sleep for 3-30 seconds
                time.sleep(random.randint(3, 5))
                continue

        if response is None:
            raise ValueError(
                f"Failed to get response from OpenAI after max retries: {error_message}"
            )

        if log_to_history:
            self.message_history = api_call_input.copy()
        self.message_history.append(response.choices[0].message)

        tool_calls: list[ToolCall] = []
        content = response.choices[0].message.content
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        call_id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments)
                        if tool_call.function.arguments
                        else {},
                        id=tool_call.id,
                    )
                )

        usage = None
        if response.usage:
            usage = LLMUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                cache_read_input_tokens=response.usage.prompt_tokens_details.cached_tokens,
                reasoning_tokens=response.usage.completion_tokens_details.reasoning_tokens if response.usage.completion_tokens_details else 0,
            )

        llm_response = LLMResponse(
            content=content,
            usage=usage,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls if len(tool_calls) > 0 else None,
        )

        return llm_response

    async def get_full_completion_stream(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam],
        model_parameters: ModelParameters
    ) -> ChatCompletion:
        """Send chat messages to OpenAI with optional tool support."""
        completion_data = {
            "id": None,
            "created": None,
            "model": None,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "", "tool_calls": []}}],
            "usage": None
        }
        stream: AsyncGenerator[ChatCompletionChunk, None] = await self.client.chat.completions.create(
            messages=messages,
            model=model_parameters.model,
            tools=tools if tools else openai.NOT_GIVEN,
            temperature=model_parameters.temperature
            if "o3" not in model_parameters.model
            else openai.NOT_GIVEN,
            top_p=model_parameters.top_p,
            stream=True,
        )

         # 处理流式响应
        async for chunk in stream:
            # 收集元数据 (只出现一次)
            chunk: ChatCompletionChunk = chunk
            if completion_data["id"] is None:
                completion_data["id"] = chunk.id
                completion_data["created"] = chunk.created
                completion_data["model"] = chunk.model

            # 处理内容增量
            if chunk.choices:
                choice = chunk.choices[0]
                delta = choice.delta
                
                # 收集文本内容
                if delta.content is not None:
                    completion_data["choices"][0]["message"]["content"] += delta.content
                
                # 收集工具调用
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        # 处理新工具调用
                        if tool_call.index >= len(completion_data["choices"][0]["message"]["tool_calls"]):
                            completion_data["choices"][0]["message"]["tool_calls"].append({
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            })
                        # 追加现有工具调用的参数
                        else:
                            current_tool = completion_data["choices"][0]["message"]["tool_calls"][tool_call.index]
                            current_tool["function"]["arguments"] += tool_call.function.arguments
 
        # 重建 ChatCompletion 对象
        return ChatCompletion(
            id=completion_data["id"],
            created=completion_data["created"],
            model=completion_data["model"],
            object="chat.completion",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=completion_data["choices"][0]["message"]["content"],
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id=tool_call["id"],
                                type=tool_call["type"],
                                function=tool_call["function"]
                            ) for tool_call in completion_data["choices"][0]["message"]["tool_calls"]
                        ]
                    ),
                    finish_reason="stop"  # 流式结束时通常为stop
                )
            ],
            usage=None  # 流式响应不包含usage数据
        )
                


    @override
    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current model supports tool calling."""
        # currently all models support tool calling
        return True

    def parse_messages(self, messages: list[LLMMessage]) -> list[ChatCompletionMessageParam]:
        """Parse the messages to OpenAI format."""
        openai_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            if msg.tool_result:
                openai_messages.append(self.parse_tool_call_result(msg.tool_result))
            elif msg.tool_call:
                #openai_messages.append(self.parse_tool_call(msg.tool_call))
                raise("not supported")
            else:
                if not msg.content:
                    raise ValueError("Message content is required")
                if msg.role == "system":
                    openai_messages.append({"role": "system", "content": msg.content})
                elif msg.role == "user":
                    openai_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    openai_messages.append(
                        {"role": "assistant", "content": msg.content}
                    )
                else:
                    raise ValueError(f"Invalid message role: {msg.role}")
        return openai_messages

    #def parse_tool_call(self, tool_call: ToolCall) -> ChatCompletionToolMessageParam:
    #    """Parse the tool call from the LLM response."""

    #    return ChatCompletionToolCallParam(
    #        call_id=tool_call.call_id,
    #        name=tool_call.name,
    #        arguments=json.dumps(tool_call.arguments),
    #        type="function_call",
    #    )

    def parse_tool_call_result(
        self, tool_call_result: ToolResult
    ) -> ChatCompletionToolMessageParam:
        """Parse the tool call result from the LLM response to FunctionCallOutput format."""
        result_content: str = ""
        if tool_call_result.result is not None:
            result_content += str(tool_call_result.result)
        if tool_call_result.error:
            result_content += f"\nError: {tool_call_result.error}"
        result_content = result_content.strip()

        return ChatCompletionToolMessageParam(
            role="tool",
            content=result_content,
            tool_call_id=tool_call_result.call_id,
        )

    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current client supports tool calling."""
        return hasattr(
            self.client, "supports_tool_calling"
        ) and self.client.supports_tool_calling(model_parameters)
