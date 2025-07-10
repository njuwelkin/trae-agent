# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""OpenAI API client wrapper with tool integration."""

import json
import os
import random
import time
from typing import override

import openai
from openai.types.responses import (
    FunctionToolParam,
    ResponseFunctionToolCallParam,
    ResponseInputParam,
    
)
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionToolParam,
    ChatCompletionToolMessageParam
)
from openai.types.responses.response_input_param import FunctionCallOutput

from openai.types.shared_params import FunctionDefinition

from ..tools.base import Tool, ToolCall, ToolResult
from ..utils.config import ModelParameters
from .base_client import BaseLLMClient
from .llm_basics import LLMMessage, LLMResponse, LLMUsage


class OpenAIClient(BaseLLMClient):
    """OpenAI client wrapper with tool schema generation."""

    def __init__(self, model_parameters: ModelParameters):
        super().__init__(model_parameters)

        if self.api_key == "":
            self.api_key: str = os.getenv("OPENAI_API_KEY", "")

        if self.api_key == "":
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY in environment variables or config file."
            )

        self.client: openai.OpenAI = openai.OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        self.message_history: list[ChatCompletionMessageParam] = []
        #self.message_history: ResponseInputParam = []

    @override
    def set_chat_history(self, messages: list[LLMMessage]) -> None:
        """Set the chat history."""
        self.message_history = self.parse_messages(messages)

    @override
    def chat(
        self,
        messages: list[LLMMessage],
        model_parameters: ModelParameters,
        tools: list[Tool] | None = None,
        reuse_history: bool = True,
    ) -> LLMResponse:
        """Send chat messages to OpenAI with optional tool support."""
        #openai_messages: ResponseInputParam = self.parse_messages(messages)
        openai_messages: list[ChatCompletionMessageParam] = self.parse_messages(messages)

        tool_schemas = None
        if tools:
            tool_schemas = [
                #FunctionToolParam(
                #    name=tool.name,
                #    description=tool.description,
                #    parameters=tool.get_input_schema(),
                #    strict=True,
                #    type="function",
                #)
                ChatCompletionToolParam(
                    type="function",
                    function=FunctionDefinition(
                        name=tool.name,
                        description=tool.description,
                        parameters=tool.get_input_schema(),
                        strict=True
                    )
                )
                for tool in tools
            ]

        #api_call_input: ResponseInputParam = []
        api_call_input: list[ChatCompletionMessageParam] = []
        if reuse_history:
            api_call_input.extend(self.message_history)
        api_call_input.extend(openai_messages)

        response = None
        error_message = ""
        for i in range(model_parameters.max_retries):
            try:
                #response = self.client.responses.create(
                #    input=api_call_input,
                response = self.client.chat.completions.create(
                    messages=api_call_input,
                    model=model_parameters.model,
                    tools=tool_schemas if tool_schemas else openai.NOT_GIVEN,
                    temperature=model_parameters.temperature
                    if "o3" not in model_parameters.model
                    else openai.NOT_GIVEN,
                    top_p=model_parameters.top_p,
                )
                break
            except Exception as e:
                error_message += f"Error {i + 1}: {str(e)}\n"
                # Randomly sleep for 3-30 seconds
                time.sleep(random.randint(3, 30))
                continue

        if response is None:
            raise ValueError(
                f"Failed to get response from OpenAI after max retries: {error_message}"
            )

        #self.message_history = api_call_input + response.output
        self.message_history = api_call_input.copy()
        self.message_history.append(response.choices[0].message)

        #content = ""
        tool_calls: list[ToolCall] = []
        content = response.choices[0].message.content
        #if isinstance(response.choices[0].message, ChatCompletionAssistantMessageParam):
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
        """
        for output_block in response.output:
            if output_block.type == "function_call":
                tool_calls.append(
                    ToolCall(
                        call_id=output_block.call_id,
                        name=output_block.name,
                        arguments=json.loads(output_block.arguments)
                        if output_block.arguments
                        else {},
                        id=output_block.id,
                    )
                )
            elif output_block.type == "message":
                content = "".join(
                    content_block.text
                    for content_block in output_block.content
                    if content_block.type == "output_text"
                )
        """

        usage = None
        if response.usage:
            usage = LLMUsage(
                #input_tokens=response.usage.input_tokens,
                input_tokens=response.usage.prompt_tokens,
                #output_tokens=response.usage.output_tokens,
                output_tokens=response.usage.completion_tokens,
                #cache_read_input_tokens=response.usage.input_tokens_details.cached_tokens,
                cache_read_input_tokens=response.usage.prompt_tokens_details.cached_tokens,
                #reasoning_tokens=response.usage.output_tokens_details.reasoning_tokens,
                reasoning_tokens=response.usage.completion_tokens_details.reasoning_tokens if response.usage.completion_tokens_details else 0,
            )

        llm_response = LLMResponse(
            content=content,
            usage=usage,
            model=response.model,
            #finish_reason=response.status,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls if len(tool_calls) > 0 else None,
        )

        # Record trajectory if recorder is available
        if self.trajectory_recorder:
            self.trajectory_recorder.record_llm_interaction(
                messages=messages,
                response=llm_response,
                provider="openai",
                model=model_parameters.model,
                tools=tools,
            )

        return llm_response

    @override
    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current model supports tool calling."""

        if "o1-mini" in model_parameters.model:
            return False

        tool_capable_models = [
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.5",
            "o1",
            "o3",
            "o3-mini",
            "o4-mini",
            "deepseek-chat"
        ]
        return any(model in model_parameters.model for model in tool_capable_models)

    #def parse_messages(self, messages: list[LLMMessage]) -> ResponseInputParam:
    def parse_messages(self, messages: list[LLMMessage]) -> list[ChatCompletionMessageParam]:
        """Parse the messages to OpenAI format."""
        #openai_messages: list[ChatCompletionMessageParam] = []
        openai_messages: list[ChatCompletionMessageParam] = []
        for msg in messages:
            if msg.tool_result:
                openai_messages.append(self.parse_tool_call_result(msg.tool_result))
            elif msg.tool_call:
                openai_messages.append(self.parse_tool_call(msg.tool_call))
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

    #def parse_tool_call(self, tool_call: ToolCall) -> ResponseFunctionToolCallParam:
    def parse_tool_call(self, tool_call: ToolCall) -> ChatCompletionToolMessageParam:
        """Parse the tool call from the LLM response."""
        #return ResponseFunctionToolCallParam(
        #    call_id=tool_call.call_id,
        #    name=tool_call.name,
        #    arguments=json.dumps(tool_call.arguments),
        #    type="function_call",
        #)
        return ChatCompletionToolCallParam(
            call_id=tool_call.call_id,
            name=tool_call.name,
            arguments=json.dumps(tool_call.arguments),
            type="function_call",
        )

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

        #return FunctionCallOutput(
        #    type="function_call_output",  # Explicitly set the type field
        #    call_id=tool_call_result.call_id,
        #    output=result_content,
        #)
        return ChatCompletionToolMessageParam(
            role="tool",
            content=result_content,
            tool_call_id=tool_call_result.call_id,
        )
