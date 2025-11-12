"""Synthesis service for generating natural language answers from retrieved chunks."""

import logging
from typing import Optional

from src.domain.models.knowledge import KnowledgeItem
from src.infrastructure.external.llm.providers.base import ILLMProvider
from src.shared.config.settings import RAGSettings

logger = logging.getLogger(__name__)


class SynthesisService:
    """Service for synthesizing natural language answers from knowledge chunks.
    
    This service takes a user query and retrieved knowledge chunks, then uses an
    LLM to generate a coherent, natural language answer based solely on the
    provided context.
    """

    async def synthesize(
        self,
        query: str,
        chunks: list[KnowledgeItem],
        llm_provider: ILLMProvider,
        settings: RAGSettings,
    ) -> Optional[str]:
        """Generate a synthesized natural language answer from knowledge chunks.
        
        Args:
            query: The original user query/question.
            chunks: List of retrieved KnowledgeItem objects containing relevant context.
            llm_provider: The LLM provider to use for synthesis.
            settings: RAG settings containing synthesis configuration.
            
        Returns:
            Synthesized answer as a string, or None if synthesis fails or no chunks provided.
        """
        # Handle empty chunks case
        if not chunks:
            logger.warning("No chunks provided for synthesis")
            return None

        try:
            # Build the synthesis prompt
            messages = self._build_synthesis_prompt(query, chunks, settings)

            # Call LLM provider to generate completion
            synthesized_answer = await llm_provider.generate_completion(
                messages=messages,
                model=settings.agentic_rag_model,
                max_tokens=settings.agentic_rag_max_tokens,
                temperature=settings.agentic_rag_temperature,
            )

            logger.info(f"Successfully synthesized answer for query: {query[:50]}...")
            return synthesized_answer.strip()

        except Exception as e:
            # Graceful degradation: Log error but don't fail the entire query
            logger.warning(f"Failed to synthesize answer: {e}")
            return None

    def _build_synthesis_prompt(
        self,
        query: str,
        chunks: list[KnowledgeItem],
        settings: RAGSettings,
    ) -> list[dict[str, str]]:
        """Build the prompt for LLM synthesis.
        
        Args:
            query: The user's query.
            chunks: Retrieved knowledge chunks.
            settings: RAG settings with system prompt.
            
        Returns:
            List of message dicts in the format required by ILLMProvider.
        """
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[Chunk {i}]\n{chunk.chunk_text}\n")

        context_text = "\n".join(context_parts)

        # Build user prompt with query and context
        user_prompt = f"""Based on the following context from the knowledge base, please answer this question:

Question: {query}

Context:
{context_text}

Please provide a clear, accurate answer based solely on the information in the context above. If the context doesn't contain enough information to fully answer the question, please indicate what information is available and what is missing."""

        # Return messages in the format expected by LLM provider
        return [
            {"role": "system", "content": settings.agentic_rag_system_prompt},
            {"role": "user", "content": user_prompt},
        ]
