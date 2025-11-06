# Database Schema
This schema is designed for PostgreSQL and includes the pgvector extension for vector storage and search, as required by the PRD. The vector dimensions are assumed to be 1536, based on the text-embedding-3-small model default from the Contextiva README.

```sql
-- Enable the pgvector extension (Required by Story 1.2)
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for Projects (Aggregate Root) (from Story 1.3)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Active',
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Table for Documents (from Story 2.1)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    content_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_documents_project_id ON documents(project_id);

-- Table for Tasks (from Story 2.1)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Todo',
    priority TEXT DEFAULT 'Medium',
    assignee UUID, -- Can be linked to a future User table
    dependencies UUID[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);

-- Table for Knowledge Items (from Story 2.1)
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL, -- Dimension from Contextiva README
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_knowledge_items_document_id ON knowledge_items(document_id);
-- Create a HNSW index for fast vector similarity search (for Story 3.1)
CREATE INDEX ON knowledge_items USING hnsw (embedding vector_cosine_ops);
```
