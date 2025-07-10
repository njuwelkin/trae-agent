class MCPClientManager:
    def __init__(self) -> None:
        self.clients = {}

    def get_client(self, provider: str) -> MCPModelClient:
        if provider not in self.clients:
            return None
        return self.clients[provider]
    
