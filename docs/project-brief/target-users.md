# Target Users

## Primary User Segment: AI Agent Developer / ML Engineer
- **Profile**: These are Python developers, ML engineers, or backend teams responsible for building, deploying, and maintaining applications that leverage Large Language Models (LLMs) and autonomous agents.
- **Current Behaviors**: They are currently writing significant amounts of boilerplate code to connect agents to vector stores, manage document ingestion pipelines (chunking, embedding), and build custom APIs for knowledge retrieval. They often find themselves managing this complex infrastructure instead of focusing on their agent's core logic.
- **Specific Needs & Pain Points**:
        - They suffer from the "infrastructure burden" of provisioning and scaling databases (like pgvector), caching layers (like Redis), and API servers.
        - They need a service, not just a library, that is production-ready with built-in security (JWT, RBAC), performance (async, connection pooling), and observability.
        - They require a solution that understands the domain of AI development, including versioning for technical documents (PRDs, specs) and hierarchical project management.

- **Goals**: To accelerate the development and deployment of sophisticated, knowledgeable, and reliable AI agents by integrating a pre-built, production-grade knowledge engine.

## Secondary User Segment: AI Agent (Programmatic Client)
- **Profile**: An autonomous software program (e.g., a BMad agent, a custom-built agent) that needs to programmatically access external knowledge to perform complex tasks.
- **Current Behaviors**: The agent often operates statelessly or relies on simple, in-memory vector stores. It lacks long-term, persistent memory and the context of a "project."
- **Specific Needs & Pain Points**:
        - Cannot manage complex, multi-step projects that require cumulative knowledge.
        - Retrieves irrelevant or outdated information because the underlying knowledge base lacks document versioning or advanced retrieval strategies.

- **Goals**: To query a persistent, version-controlled knowledge base via a clean API (REST or MCP) to retrieve highly relevant, contextual information on demand. This enables the agent to complete tasks more accurately, effectively, and with a consistent "memory."
