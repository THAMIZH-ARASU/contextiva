# Data Models

## Project
**Purpose**: The Project is the top-level aggregate root. It acts as the primary container for all other domain objects, including documents, tasks, and knowledge items. 
### Key Attributes:
- `id`: UUID - Primary key
- `name`: str - The user-defined name of the project
- `description`: str (optional) - A brief description
- `status`: str - (e.g., "Active", "Archived")
- `tags`: list[str] (optional) - Metadata tags for organization 
### Relationships:
- One `Project` has MANY `Documents`
- One `Project` has MANY `Tasks`

## Document
**Purpose**: Represents a single source of knowledge within a Project. This entity manages the metadata and versioning of the knowledge source. 
### Key Attributes:
- `id`: UUID - Primary key
- `project_id`: UUID - Foreign key to Project
- `name`: str - The name of the document (e.g., "PRD.md")
- `type`: str - (e.g., "PDF", "Markdown", "DOCX", "WebCrawl")
- `version`: str - Semantic version (e.g., "v1.0.0")
- `content_hash`: str - A hash of the file content to detect changes 
### Relationships:
- Belongs to ONE `Project`
- One `Document` (version) has MANY `KnowledgeItems`

## Task
**Purpose**: Represents a unit of work associated with a Project. 
### Key Attributes:
- `id`: UUID - Primary key
- `project_id`: UUID - Foreign key to Project
- `title`: str - The name of the task
- `status`: str - (e.g., "Todo", "InProgress", "Done")
- `priority`: str (optional) - (e.g., "Low", "Medium", "High")
- `assignee`: UUID (optional) - Foreign key to a User
- `dependencies`: list[UUID] (optional) - List of other Task IDs 
### Relationships:
- Belongs to ONE `Project`

## KnowledgeItem
**Purpose**: Represents a single, embeddable chunk of text (and its vector) derived from a Document. This is the core unit of retrieval for the RAG system. 
### Key Attributes:
- `id`: UUID - Primary key
- `document_id`: UUID - Foreign key to Document
- `chunk_text`: str - The raw text of the chunk
- `embedding`: Vector - The vector embedding of the chunk (from pgvector)
- `metadata`: JSON - (e.g., page number, source URL, chunk character indices)
### Relationships:
- Belongs to ONE `Document`
