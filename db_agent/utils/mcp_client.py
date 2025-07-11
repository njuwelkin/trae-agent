import asyncio
from typing import Any, Dict, List, Optional, Union
from fastmcp import Client as FastMCPClient
from fastmcp.client.transports import (
    StdioTransport,
    StreamableHttpTransport,
    SSETransport
)
from mcp.types import Tool

class MCPClientBase:
    """Base class for MCP clients using fastmcp framework"""
    def __init__(self, server_source: Union[str, Dict], **kwargs):
        """
        Initialize MCP client
        
        :param server_source: Server connection source
            - URL (http/https) for HTTP/SSE transport
            - File path (.py/.js) for stdio transport
            - Dict for multi-server config
        :param kwargs: Additional client options
            timeout: Request timeout in seconds
            auth: Authentication handler (e.g., BearerAuth)
            headers: Custom HTTP headers
            env: Environment variables for stdio servers
        """
        self.client = FastMCPClient(server_source, **kwargs)
        self.connected = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.client.__aenter__()
        print("enter")
        self.connected = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        print(f"exit {exc_type} {exc_val} {exc_tb}")
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        self.connected = False

    async def ping(self) -> bool:
        """Verify server connectivity"""
        if not self.connected:
            raise RuntimeError("Not connected to server")
        await self.client.ping()
        return True

    async def list_tools(self) -> List[Tool]:
        """List available tools on server"""
        if not self.connected:
            raise RuntimeError("Not connected to server")
        return await self.client.list_tools()
        #await self.client.__aenter__()
        #tools = await self.client.list_tools()

    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a server tool with parameters
        
        :param tool_name: Name of registered tool
        :param parameters: Dictionary of input parameters
        :return: Tool execution result
        """
        if not self.connected:
            raise RuntimeError("Not connected to server")
        return await self.client.call_tool(tool_name, parameters)

    async def get_resources(self) -> List[Dict]:
        """List available resources on server"""
        if not self.connected:
            raise RuntimeError("Not connected to server")
        return await self.client.list_resources()

    async def read_resource(self, uri: str) -> str:
        """
        Read resource content by URI
        
        :param uri: Resource URI (e.g., "greet://{name}")
        :return: Resource content as string
        """
        if not self.connected:
            raise RuntimeError("Not connected to server")
        resource = await self.client.read_resource(uri)
        return resource.text

    async def get_prompts(self) -> List[Dict]:
        """List available prompt templates"""
        if not self.connected:
            raise RuntimeError("Not connected to server")
        return await self.client.list_prompts()

    async def render_prompt(self, prompt_name: str, arguments: Dict[str, Any]) -> str:
        """
        Render prompt template with arguments
        
        :param prompt_name: Name of registered prompt
        :param arguments: Variables for template rendering
        :return: Rendered prompt text
        """
        if not self.connected:
            raise RuntimeError("Not connected to server")
        prompt = await self.client.get_prompt(prompt_name, arguments)
        return prompt.text

    async def test_list_tools(self):
        await self.__aenter__()
        tools = await self.list_tools()
        print(tools)
        await self.__aexit__(None, None, None)



class SSEClient(MCPClientBase):
    """Client for Server-Sent Events (SSE) transport"""
    def __init__(self, url: str, **kwargs):
        """
        :param url: SSE endpoint URL (e.g., "http://localhost:8000/sse")
        """
        transport = SSETransport(url=url, headers=kwargs.get("headers", {}))
        super().__init__(transport, **kwargs)


class StreamableHttpClient(MCPClientBase):
    """Client for Streamable HTTP transport"""
    def __init__(self, url: str, **kwargs):
        """
        :param url: HTTP endpoint URL (e.g., "http://localhost:8000/mcp")
        """
        transport = StreamableHttpTransport(url=url, headers=kwargs.get("headers", {}))
        super().__init__(transport, **kwargs)


class StdioClient(MCPClientBase):
    """Client for STDIO transport (local scripts)"""
    def __init__(self, script_path: str, **kwargs):
        """
        :param script_path: Path to server script (e.g., "./server.py")
        """
        transport = StdioTransport(
            command="python",
            args=[script_path],
            env=kwargs.get("env", {}),
            cwd=kwargs.get("cwd", "."),
            keep_alive=kwargs.get("keep_alive", True)
        )
        super().__init__(transport, **kwargs)


class MemoryClient(MCPClientBase):
    """In-memory client for testing"""
    def __init__(self, server_instance: Any, **kwargs):
        """
        :param server_instance: FastMCP server instance
        """
        super().__init__(server_instance, **kwargs)


async def test():
    # HTTP Client Example
    client = SSEClient("http://localhost:9000/sse")
    t = await client.test_list_tools()
    print(t)
    async with SSEClient("http://localhost:9000/sse") as client:
        if await client.ping():
            print("Server connected")
        
        # Get available tools
        tools = await client.list_tools()
        print(tools[0])
        #print(f"Available tools: {[t['name'] for t in tools]}")

    #    resources = await client.get_resources()
    #    print(resources)

    #    prompts = await client.get_prompts()
    #    print(prompts)
        
        # Call calculator tool
        #result = await client.call_tool("calculate", {"a": 5, "b": 3, "op": "*"})
        #print(f"Calculation result: {result.data}")  # 15 :cite[1]:cite[2]
    #tools = await client.get_tools()
    #print(tools)

if __name__ == "__main__":
    asyncio.run(test())