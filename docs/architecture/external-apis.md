# External APIs

## LLM Providers (e.g., OpenAI)
- **Purpose**: Provides core LLM completions (for Agentic RAG synthesis, re-ranking) and text-embedding services (for ingestion).
- **Documentation**: https://platform.openai.com/docs
- **Base URL(s)**: https://api.openai.com
- **Authentication**: API Key (Bearer Token) loaded from environment variables (LLM_API_KEY).
- **Rate Limits**: Varies based on the user's API key and organizational tier.
- **Key Endpoints Used**:
        - POST `/v1/chat/completions` - For Agentic RAG and re-ranking.
        - POST `/v1/embeddings` - For embedding document chunks.
- **Integration Notes**: This is a primary, pluggable integration managed by the LLM/Embedding Provider Factory (Story 2.2). The system must be resilient to this API's rate limits and errors.

## LLM Providers (e.g., Anthropic, Ollama, OpenRouter)
- **Purpose**: Serve as alternative, pluggable providers for LLM and/or embedding services, as per PRD requirement NFR8.
- **Documentation**: Varies by provider (e.g., https://docs.anthropic.com/, https://ollama.com/).
- **Base URL(s)**: Varies (e.g., https://api.anthropic.com, http://localhost:11434 for Ollama).
- **Authentication**: API Key (or None for local Ollama).
- **Rate Limits**: Varies.
- **Key Endpoints Used**:
        - Varies (e.g., POST `/v1/messages` for Anthropic, POST `/api/generate` for Ollama).
- **Integration Notes**: The LLM/Embedding Provider Factory will abstract the differences between these APIs, but their specific endpoints and request/response models must be handled by the concrete provider implementations.

## Web Crawler (General HTTP/Web)
- **Purpose**: To fetch and parse HTML content from user-specified URLs for knowledge ingestion (PRD Story 2.6).
- **Documentation**: N/A (Uses standard HTTP GET requests).
- **Base URL(s)**: N/A (User-provided).
- **Authentication**: N/A (Assumes public web access).
- **Rate Limits**: N/A (Assumes public web access).
- **Key Endpoints Used**:
        - GET `{user_provided_url}` - To fetch raw HTML.
- **Integration Notes**: This integration is handled by the Web Crawler component. It must be respectful of robots.txt (as noted in Story 2.6) and include a reasonable default timeout.
