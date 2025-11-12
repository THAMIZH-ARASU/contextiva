"""MCP server implementation for Contextiva.

This module implements the main MCP server that exposes Contextiva's
knowledge engine functionality via the Model Context Protocol.
"""

import asyncio
import logging
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.mcp.context import MCPContext
from src.mcp.tools.documents import IngestDocumentTool
from src.mcp.tools.projects import CreateProjectTool
from src.mcp.tools.rag import QueryKnowledgeTool
from src.shared.config.settings import load_settings
from src.shared.utils.errors import UnauthorizedAccessError

logger = logging.getLogger(__name__)


class ContextivaMCPServer:
    """MCP server for Contextiva knowledge engine.
    
    Exposes three main tools:
    - create_project: Create a new project
    - ingest_document: Ingest a document into a project
    - query_knowledge: Query knowledge using RAG
    """

    def __init__(self) -> None:
        """Initialize MCP server."""
        self.settings = load_settings()
        self.context = MCPContext(settings=self.settings)
        self.server = Server("contextiva")
        
        # Initialize tools
        self.create_project_tool = CreateProjectTool(context=self.context)
        self.ingest_document_tool = IngestDocumentTool(context=self.context)
        self.query_knowledge_tool = QueryKnowledgeTool(context=self.context)
        
        # Register handlers
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available MCP tools.
            
            Returns:
                List of available tools with their schemas.
            """
            return [
                Tool(**self.create_project_tool.get_schema()),
                Tool(**self.ingest_document_tool.get_schema()),
                Tool(**self.query_knowledge_tool.get_schema()),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
            """Execute an MCP tool.
            
            Args:
                name: Tool name to execute.
                arguments: Tool arguments including _auth_token.
                
            Returns:
                Sequence of TextContent with tool results.
                
            Raises:
                ValueError: If tool not found or authentication fails.
            """
            # Extract and validate authentication token
            auth_token = arguments.pop("_auth_token", None)
            
            if not auth_token:
                raise ValueError("Authentication token required")
            
            try:
                user = await self.context.authenticate_user(auth_token)
            except UnauthorizedAccessError as e:
                raise ValueError(f"Authentication failed: {e}")
            
            # Add authenticated user to arguments
            arguments["user"] = user
            
            # Execute tool based on name
            if name == "create_project":
                result = await self.create_project_tool.execute(**arguments)
            elif name == "ingest_document":
                result = await self.ingest_document_tool.execute(**arguments)
            elif name == "query_knowledge":
                result = await self.query_knowledge_tool.execute(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            # Return result as TextContent
            import json
            return [TextContent(type="text", text=json.dumps(result))]
    
    async def run(self) -> None:
        """Run the MCP server using stdio transport.
        
        This starts the server and handles incoming MCP requests.
        """
        logger.info("Starting Contextiva MCP server...")
        
        # Initialize context
        await self.context.initialize()
        
        try:
            # Run server with stdio transport
            async with stdio_server() as (read_stream, write_stream):
                logger.info("MCP server running on stdio")
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        finally:
            # Cleanup
            logger.info("Shutting down MCP server...")
            await self.context.cleanup()
            logger.info("MCP server shut down successfully")


async def main() -> None:
    """Main entry point for MCP server."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Create and run server
    server = ContextivaMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
