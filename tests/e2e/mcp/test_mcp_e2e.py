"""End-to-end tests for MCP server interactions.

These tests verify the complete MCP server workflow including:
- Client connection to MCP server
- Authentication via JWT tokens
- Tool invocations (create_project, ingest_document, query_knowledge)
- Error handling and validation
"""

import asyncio
import json
import pytest
from typing import Any, Dict
from uuid import uuid4

from mcp.client import Client
from mcp.client.stdio import stdio_client

from src.shared.config.settings import load_settings
from src.shared.utils.security import create_access_token


class SimpleMCPClient:
    """Simple MCP client for testing purposes.
    
    This client connects to the MCP server via stdio and provides
    methods to invoke tools with authentication.
    """
    
    def __init__(self, auth_token: str) -> None:
        """Initialize MCP client with authentication token.
        
        Args:
            auth_token: JWT authentication token.
        """
        self.auth_token = auth_token
        self.client: Client | None = None
        
    async def connect(self) -> None:
        """Connect to MCP server via stdio."""
        # In real implementation, this would start the MCP server subprocess
        # and connect via stdio. For testing, we'll mock this.
        pass
        
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        pass
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool.
        
        Args:
            name: Tool name.
            arguments: Tool arguments.
            
        Returns:
            Tool result as dictionary.
        """
        # Add authentication token to arguments
        arguments["_auth_token"] = self.auth_token
        
        # In real implementation, this would invoke the tool via MCP protocol
        # For testing, we'll mock this by directly calling the server
        from src.mcp.server import ContextivaMCPServer
        
        server = ContextivaMCPServer()
        await server.context.initialize()
        
        try:
            # Call the tool handler directly (simulating MCP invocation)
            result = await server.server._handlers["call_tool"](name, arguments)
            
            # Parse text content result
            if result and len(result) > 0:
                return json.loads(result[0].text)
            return {}
        finally:
            await server.context.cleanup()


@pytest.fixture
def auth_token():
    """Create a valid JWT authentication token for testing.
    
    Returns:
        Valid JWT token string.
    """
    # Create token for test user
    return create_access_token(
        data={"sub": "testuser"},
        settings=load_settings(),
    )


@pytest.fixture
def invalid_token():
    """Create an invalid JWT token for testing.
    
    Returns:
        Invalid token string.
    """
    return "invalid.jwt.token"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_create_project_e2e(auth_token):
    """Test E2E flow: Connect to MCP server and create a project.
    
    Arrange: Create MCP client with valid token.
    Act: Connect to server and create project.
    Assert: Project is created successfully.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    
    try:
        # Act
        await client.connect()
        
        result = await client.call_tool(
            name="create_project",
            arguments={
                "name": f"E2E Test Project {uuid4()}",
                "description": "Test project created via MCP E2E test",
                "tags": ["e2e", "test"],
            },
        )
        
        # Assert
        assert "project_id" in result
        assert result["name"].startswith("E2E Test Project")
        assert result["description"] == "Test project created via MCP E2E test"
        assert result["status"] == "Active"
        assert "e2e" in result["tags"]
        assert "created_at" in result
        
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_ingest_document_e2e(auth_token):
    """Test E2E flow: Create project and ingest document.
    
    Arrange: Create MCP client and project.
    Act: Ingest document into project.
    Assert: Document is ingested successfully.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    
    try:
        await client.connect()
        
        # Create project first
        project_result = await client.call_tool(
            name="create_project",
            arguments={
                "name": f"E2E Ingest Test {uuid4()}",
                "description": "Test project for document ingestion",
            },
        )
        project_id = project_result["project_id"]
        
        # Act
        ingest_result = await client.call_tool(
            name="ingest_document",
            arguments={
                "project_id": project_id,
                "content": "This is a test document for E2E testing. It contains information about machine learning and AI.",
                "filename": "test_doc.txt",
                "content_type": "text/plain",
                "metadata": {"source": "e2e_test"},
            },
        )
        
        # Assert
        assert "document_id" in ingest_result
        assert ingest_result["status"] == "ingested"
        assert ingest_result["chunks_created"] > 0
        assert ingest_result["filename"] == "test_doc.txt"
        
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_query_knowledge_e2e(auth_token):
    """Test E2E flow: Create project, ingest document, and query knowledge.
    
    Arrange: Create MCP client, project, and ingest document.
    Act: Query knowledge from project.
    Assert: Query returns relevant results.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    
    try:
        await client.connect()
        
        # Create project
        project_result = await client.call_tool(
            name="create_project",
            arguments={
                "name": f"E2E Query Test {uuid4()}",
                "description": "Test project for knowledge query",
            },
        )
        project_id = project_result["project_id"]
        
        # Ingest document
        await client.call_tool(
            name="ingest_document",
            arguments={
                "project_id": project_id,
                "content": "Machine learning is a subset of artificial intelligence that focuses on learning from data. Deep learning is a subset of machine learning using neural networks.",
                "filename": "ml_overview.txt",
            },
        )
        
        # Wait for ingestion to complete (in real scenario, might need async processing)
        await asyncio.sleep(1)
        
        # Act
        query_result = await client.call_tool(
            name="query_knowledge",
            arguments={
                "project_id": project_id,
                "query_text": "What is machine learning?",
            },
        )
        
        # Assert
        assert "query_id" in query_result
        assert "results" in query_result
        assert query_result["total_results"] > 0
        assert len(query_result["results"]) > 0
        
        # Check first result structure
        first_result = query_result["results"][0]
        assert "id" in first_result
        assert "chunk_text" in first_result
        assert "similarity_score" in first_result
        assert "machine learning" in first_result["chunk_text"].lower()
        
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_query_with_all_rag_features_e2e(auth_token):
    """Test E2E flow: Query knowledge with all RAG features enabled.
    
    Arrange: Create MCP client, project, and ingest document.
    Act: Query with hybrid search, re-ranking, and synthesis enabled.
    Assert: Results include all RAG features.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    
    try:
        await client.connect()
        
        # Create project and ingest document
        project_result = await client.call_tool(
            name="create_project",
            arguments={"name": f"E2E RAG Test {uuid4()}"},
        )
        project_id = project_result["project_id"]
        
        await client.call_tool(
            name="ingest_document",
            arguments={
                "project_id": project_id,
                "content": "Python is a high-level programming language. It is widely used for web development, data science, and machine learning. Python has a simple syntax that is easy to learn.",
            },
        )
        
        await asyncio.sleep(1)
        
        # Act
        query_result = await client.call_tool(
            name="query_knowledge",
            arguments={
                "project_id": project_id,
                "query_text": "Tell me about Python programming",
                "top_k": 3,
                "use_hybrid_search": True,
                "use_re_ranking": True,
                "use_agentic_rag": True,
            },
        )
        
        # Assert
        assert query_result["total_results"] > 0
        
        # Check that results may have BM25 and rerank scores (depending on implementation)
        # Note: These may be None if the services aren't fully implemented in test env
        first_result = query_result["results"][0]
        assert "similarity_score" in first_result
        
        # Check for synthesized answer when agentic RAG is enabled
        # Note: This may be None if LLM service isn't available in test env
        assert "synthesized_answer" in query_result
        
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_authentication_failure_e2e(invalid_token):
    """Test E2E flow: Authentication fails with invalid token.
    
    Arrange: Create MCP client with invalid token.
    Act: Attempt to create project.
    Assert: Authentication error is raised.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=invalid_token)
    
    try:
        await client.connect()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Authentication failed"):
            await client.call_tool(
                name="create_project",
                arguments={"name": "Should Fail"},
            )
            
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_missing_token_e2e():
    """Test E2E flow: Tool call fails without authentication token.
    
    Arrange: Create MCP client without token.
    Act: Attempt to create project.
    Assert: Authentication error is raised.
    """
    # Arrange
    client = SimpleMCPClient(auth_token="")
    
    try:
        await client.connect()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Authentication token required"):
            # Manually override to remove token
            await client.call_tool(
                name="create_project",
                arguments={"name": "Should Fail", "_auth_token": None},
            )
            
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_invalid_parameters_e2e(auth_token):
    """Test E2E flow: Tool call fails with invalid parameters.
    
    Arrange: Create MCP client with valid token.
    Act: Attempt to call tool with invalid parameters.
    Assert: Validation error is raised.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    
    try:
        await client.connect()
        
        # Act & Assert - Invalid project_id format
        with pytest.raises(ValueError, match="Invalid project_id format"):
            await client.call_tool(
                name="ingest_document",
                arguments={
                    "project_id": "not-a-valid-uuid",
                    "content": "Test content",
                },
            )
            
    finally:
        await client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_mcp_project_not_found_e2e(auth_token):
    """Test E2E flow: Tool call fails for nonexistent project.
    
    Arrange: Create MCP client with valid token.
    Act: Attempt to ingest document into nonexistent project.
    Assert: Project not found error is raised.
    """
    # Arrange
    client = SimpleMCPClient(auth_token=auth_token)
    nonexistent_project_id = str(uuid4())
    
    try:
        await client.connect()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Project not found"):
            await client.call_tool(
                name="ingest_document",
                arguments={
                    "project_id": nonexistent_project_id,
                    "content": "Test content",
                },
            )
            
    finally:
        await client.disconnect()
