"""
MCP Client Manager.
Maintains persistent sessions to Aegis MCP servers and helpers.
"""
class MCPClient:
    """Manages connections to aegis-target, aegis-kb, aegis-eval, aegis-risk."""
    def __init__(self):
        self.sessions = {}

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        # Stub for MCP stdio / localhost client tool dispatch
        pass
