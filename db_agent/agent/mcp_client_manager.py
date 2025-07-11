from typing import Dict
from db_agent.utils.mcp_client import SSEClient, MCPClientBase

class MCPClientManager:
    def __init__(self) -> None:
        self.clients: Dict[str, MCPModelClient] = {}

    def get_client(self, provider: str) -> MCPClientBase:
        # TODO: get client according to database type
        return SSEClient("http://localhost:9000/sse")
    
