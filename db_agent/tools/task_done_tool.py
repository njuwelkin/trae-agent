# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import override

from .base import Tool, ToolCallArguments, ToolExecResult, ToolParameter


class TaskDoneTool(Tool):
    """Tool to mark a task as done."""

    def __init__(self, model_provider: str | None = None, call_back: any = None) -> None:
        super().__init__(model_provider)
        self._call_back = call_back

    @override
    def get_model_provider(self) -> str | None:
        return self._model_provider

    @override
    def get_name(self) -> str:
        return "task_done"

    @override
    def get_description(self) -> str:
        return """
        Report the completion of the task.
        And/or call it whenever you think the conversation is done
        Note that you cannot call this tool before any verification is done. You can write reproduce / test script to verify your solution.
        """

    @override
    def get_parameters(self) -> list[ToolParameter]:
        return []

    @override
    async def execute(self, arguments: ToolCallArguments) -> ToolExecResult:
        if self._call_back:
            self._call_back()
        return ToolExecResult(output="Task done.")
