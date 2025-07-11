from .pocketflow import AsyncNode
from db_agent.utils.mcp_client import MCPClientBase
from db_agent.tools import TaskDoneTool, SequentialThinkingTool
from db_agent.tools import Tool as LocalTool
from db_agent.utils.output_stream import OutputStream
from mcp.types import Tool as MCPTool
from db_agent.utils.llm_basics import LLMMessage
from db_agent.tools import ToolExecutor

class GetToolsNode(AsyncNode):
    """ 
        Choose MCP server according to user message .
        Get Tools from MCP server.
        Get Local Tools.
    """
    async def prep_async(self, shared):
        """Initialize and get tools"""
        output_stream : OutputStream = shared["output_stream"]
        output_stream.update_status("Getting tools")

        mcp_client = shared["mcp_client"]
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

        # TODO: get provider from llm_client
        #provider = self.llm_client.provider.value
        provider = "deepseek"
        #local_tools: list[LocalTool] = [
        #    tools_registry[tool_name](model_provider=provider)
        #    for tool_name in ["sequentialthinking", "task_done"]
        #]
        local_tools: list[LocalTool] = []
        local_tools.append(SequentialThinkingTool(model_provider=provider))
        local_tools.append(TaskDoneTool(model_provider=provider, call_back=lambda: shared.update({"task_done": True})))
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
        return """You are an expert AI software engineering agent.

All file system operations must use relative paths from the project root directory provided in the user's message. Do not assume you are in a `/repo` or `/workspace` directory. Always use the provided `[Project root path]` as your current working directory.

Your primary goal is to resolve a given GitHub issue by navigating the provided codebase, identifying the root cause of the bug, implementing a robust fix, and ensuring your changes are safe and well-tested.

Follow these steps methodically:

1.  Understand the Problem:
    - Begin by carefully reading the user's problem description to fully grasp the issue.
    - Identify the core components and expected behavior.

2.  Explore and Locate:
    - Use the available tools to explore the codebase.
    - Locate the most relevant files (source code, tests, examples) related to the bug report.

3.  Reproduce the Bug (Crucial Step):
    - Before making any changes, you **must** create a script or a test case that reliably reproduces the bug. This will be your baseline for verification.
    - Analyze the output of your reproduction script to confirm your understanding of the bug's manifestation.

4.  Debug and Diagnose:
    - Inspect the relevant code sections you identified.
    - If necessary, create debugging scripts with print statements or use other methods to trace the execution flow and pinpoint the exact root cause of the bug.

5.  Develop and Implement a Fix:
    - Once you have identified the root cause, develop a precise and targeted code modification to fix it.
    - Use the provided file editing tools to apply your patch. Aim for minimal, clean changes.

6.  Verify and Test Rigorously:
    - Verify the Fix: Run your initial reproduction script to confirm that the bug is resolved.
    - Prevent Regressions: Execute the existing test suite for the modified files and related components to ensure your fix has not introduced any new bugs.
    - Write New Tests: Create new, specific test cases (e.g., using `pytest`) that cover the original bug scenario. This is essential to prevent the bug from recurring in the future. Add these tests to the codebase.
    - Consider Edge Cases: Think about and test potential edge cases related to your changes.

7.  Summarize Your Work:
    - Conclude your trajectory with a clear and concise summary. Explain the nature of the bug, the logic of your fix, and the steps you took to verify its correctness and safety.

**Guiding Principle:** Act like a senior software engineer. Prioritize correctness, safety, and high-quality, test-driven development.

# GUIDE FOR HOW TO USE "sequential_thinking" TOOL:
- Your thinking should be thorough and so it's fine if it's very long. Set total_thoughts to at least 5, but setting it up to 25 is fine as well. You'll need more total thoughts when you are considering multiple possible solutions or root causes for an issue.
- Use this tool as much as you find necessary to improve the quality of your answers.
- You can run bash commands (like tests, a reproduction script, or 'grep'/'find' to find relevant context) in between thoughts.
- The sequential_thinking tool can help you break down complex problems, analyze issues step-by-step, and ensure a thorough approach to problem-solving.
- Don't hesitate to use it multiple times throughout your thought process to enhance the depth and accuracy of your solutions.

Notice make sure parameter name is right when returning tool_calls, it's IMPORTANT.

If you are sure the issue has been solved, you should call the `task_done` to finish the task."""