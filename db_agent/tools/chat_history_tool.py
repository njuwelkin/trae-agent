# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import override
import json

from .base import Tool, ToolCallArguments, ToolExecResult, ToolParameter


class ChatHistoryTool(Tool):
    """Tool to mark a task as done."""

    def __init__(self, model_provider: str | None = None, call_back: any = None) -> None:
        super().__init__(model_provider)
        self._call_back = call_back

    @override
    def get_model_provider(self) -> str | None:
        return self._model_provider

    @override
    def get_name(self) -> str:
        return "chat_history"

    @override
    def get_description(self) -> str:
        return """The tool returns the chat history of current user. 
        The chat history is a list of dictionaries, each dictionary contains the role and content of a message.
        It's called when you think answering this question requires some contextual information that can be found in the chat history.
        """

    @override
    def get_parameters(self) -> list[ToolParameter]:
        return []

    @override
    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        result = []
        if self._call_back:
            result = self._call_back()
        return ToolExecResult(output=json.dumps(result))
