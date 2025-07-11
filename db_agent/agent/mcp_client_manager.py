from typing import Dict
from db_agent.utils.mcp_client import SSEClient, StdioClient, MCPClientBase

class MCPClientManager:
    def __init__(self) -> None:
        self.clients: Dict[str, MCPModelClient] = {}

    def get_client(self, provider: str) -> MCPClientBase:
        # TODO: get client according to database type
        #return SSEClient("http://localhost:9000/sse")
        return StdioClient(
            command="uv",
            args=[
                "--directory",
                "/opt/anaconda3/bin",
                "run",
                "mysql_mcp_server"
            ],
            env={
                "MYSQL_HOST": "127.0.0.1",
                "MYSQL_PORT": "3306",
                "MYSQL_USER": "root",
                "MYSQL_PASSWORD": "my-secret-pw",
                "MYSQL_DATABASE": "test"
            }
        )
    
