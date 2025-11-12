from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Required environment variable '{name}' is not set and no default provided")
    return value


def _get_int(name: str, default: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        if default is None:
            raise RuntimeError(f"Required environment variable '{name}' is not set and no default provided")
        return default
    return int(raw)


@dataclass(frozen=True)
class AppSettings:
    environment: str
    host: str
    port: int


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    db: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        user_enc = quote_plus(self.user)
        pwd_enc = quote_plus(self.password)
        return f"postgresql://{user_enc}:{pwd_enc}@{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    db: int


@dataclass(frozen=True)
class SecuritySettings:
    jwt_secret: str
    jwt_algorithm: str
    jwt_expires_minutes: int


@dataclass(frozen=True)
class LLMSettings:
    """Configuration for LLM and embedding providers."""

    llm_provider: str
    embedding_provider: str
    openai_api_key: str | None
    anthropic_api_key: str | None
    ollama_base_url: str
    openrouter_api_key: str | None
    default_llm_model: str
    default_embedding_model: str


@dataclass(frozen=True)
class FileUploadSettings:
    """Configuration for file upload and processing."""

    max_file_size_mb: int
    allowed_extensions: list[str]
    chunk_size_chars: int
    chunk_overlap_chars: int
    preserve_sentence_boundaries: bool


@dataclass(frozen=True)
class CrawlerSettings:
    """Configuration for web crawler."""

    timeout_seconds: int
    user_agent: str
    respect_robots_txt: bool
    max_retries: int


@dataclass(frozen=True)
class RAGSettings:
    """Configuration for RAG (Retrieval-Augmented Generation) query."""

    default_top_k: int
    max_top_k: int
    # Hybrid search configuration
    use_hybrid_search: bool
    hybrid_search_weight_vector: float
    hybrid_search_weight_bm25: float
    # Re-ranking configuration
    use_reranking: bool
    reranking_model: str
    reranking_top_k: int
    # Redis caching configuration
    cache_enabled: bool
    cache_ttl: int
    cache_key_prefix: str
    # Agentic RAG configuration
    use_agentic_rag: bool
    agentic_rag_model: str
    agentic_rag_max_tokens: int
    agentic_rag_temperature: float
    agentic_rag_system_prompt: str


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    db: DatabaseSettings
    redis: RedisSettings
    security: SecuritySettings
    llm: LLMSettings
    file_upload: FileUploadSettings
    crawler: CrawlerSettings
    rag: RAGSettings


def load_settings() -> Settings:
    return Settings(
        app=AppSettings(
            environment=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=_get_int("APP_PORT", 8000),
        ),
        db=DatabaseSettings(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=_get_int("POSTGRES_PORT", 5432),
            db=os.getenv("POSTGRES_DB", "contextiva"),
            user=os.getenv("POSTGRES_USER", "contextiva"),
            password=os.getenv("POSTGRES_PASSWORD", "changeme"),
        ),
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=_get_int("REDIS_PORT", 6379),
            db=_get_int("REDIS_DB", 0),
        ),
        security=SecuritySettings(
            jwt_secret=os.getenv("JWT_SECRET", "change-this-secret"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expires_minutes=_get_int("JWT_EXPIRES_MINUTES", 60),
        ),
        llm=LLMSettings(
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            embedding_provider=os.getenv("LLM_EMBEDDING_PROVIDER", "openai"),
            openai_api_key=os.getenv("LLM_OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("LLM_ANTHROPIC_API_KEY"),
            ollama_base_url=os.getenv("LLM_OLLAMA_BASE_URL", "http://localhost:11434"),
            openrouter_api_key=os.getenv("LLM_OPENROUTER_API_KEY"),
            default_llm_model=os.getenv("LLM_DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            default_embedding_model=os.getenv("LLM_DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small"),
        ),
        file_upload=FileUploadSettings(
            max_file_size_mb=_get_int("MAX_FILE_SIZE_MB", 10),
            allowed_extensions=[".md", ".pdf", ".docx", ".html"],
            chunk_size_chars=_get_int("CHUNK_SIZE_CHARS", 2048),
            chunk_overlap_chars=_get_int("CHUNK_OVERLAP_CHARS", 200),
            preserve_sentence_boundaries=os.getenv("PRESERVE_SENTENCE_BOUNDARIES", "true").lower() == "true",
        ),
        crawler=CrawlerSettings(
            timeout_seconds=_get_int("CRAWLER_TIMEOUT_SECONDS", 30),
            user_agent=os.getenv("CRAWLER_USER_AGENT", "Contextiva/1.0"),
            respect_robots_txt=os.getenv("CRAWLER_RESPECT_ROBOTS_TXT", "true").lower() == "true",
            max_retries=_get_int("CRAWLER_MAX_RETRIES", 3),
        ),
        rag=RAGSettings(
            default_top_k=_get_int("RAG_DEFAULT_TOP_K", 5),
            max_top_k=_get_int("RAG_MAX_TOP_K", 50),
            use_hybrid_search=os.getenv("RAG_USE_HYBRID_SEARCH", "false").lower() == "true",
            hybrid_search_weight_vector=float(os.getenv("RAG_HYBRID_WEIGHT_VECTOR", "0.7")),
            hybrid_search_weight_bm25=float(os.getenv("RAG_HYBRID_WEIGHT_BM25", "0.3")),
            use_reranking=os.getenv("RAG_USE_RERANKING", "false").lower() == "true",
            reranking_model=os.getenv("RAG_RERANKING_MODEL", "gpt-4o-mini"),
            reranking_top_k=_get_int("RAG_RERANKING_TOP_K", 10),
            cache_enabled=os.getenv("RAG_CACHE_ENABLED", "true").lower() == "true",
            cache_ttl=_get_int("RAG_CACHE_TTL", 3600),
            cache_key_prefix=os.getenv("RAG_CACHE_KEY_PREFIX", "rag:query:"),
            # Agentic RAG configuration
            use_agentic_rag=os.getenv("RAG_USE_AGENTIC", "false").lower() == "true",
            agentic_rag_model=os.getenv("RAG_AGENTIC_MODEL", "stable-code:3b-code-q5_K_M"),
            agentic_rag_max_tokens=_get_int("RAG_AGENTIC_MAX_TOKENS", 1000),
            agentic_rag_temperature=float(os.getenv("RAG_AGENTIC_TEMPERATURE", "0.3")),
            agentic_rag_system_prompt=os.getenv(
                "RAG_AGENTIC_SYSTEM_PROMPT",
                "You are a helpful AI assistant. Based on the provided context from the knowledge base, "
                "answer the user's question accurately and concisely. Only use information from the given "
                "context. If the context doesn't contain enough information to answer the question, say so. "
                "Do not make up or infer information that isn't in the context."
            ),
        ),
    )


