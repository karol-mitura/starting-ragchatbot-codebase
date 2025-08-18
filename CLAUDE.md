# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) chatbot system for course materials. It combines semantic search with AI generation to answer questions about educational content. The system uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for user interaction.

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Dependencies
```bash
# Install all dependencies
uv sync

# The application uses uv for package management, not pip
```

### Environment Setup
```bash
# Required environment variable in .env file:
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Code Quality Tools
```bash
# Run all quality checks (formatting, linting, type checking)
uv run python scripts/quality_check.py

# Format code with black and sort imports
uv run python scripts/format.py

# Run linting checks
uv run python scripts/lint.py

# Run type checking
uv run python scripts/typecheck.py

# Individual tools
uv run black .                    # Format code
uv run isort .                    # Sort imports
uv run flake8 backend/ main.py scripts/  # Lint code
uv run mypy backend/ main.py scripts/    # Type check
```

### Access Points
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

### Core Components Flow
The system follows a layered architecture with clear separation of concerns:

1. **Frontend Layer** (`frontend/`)
   - `script.js`: Handles user interactions, HTTP requests, session management
   - `index.html`: Web interface with chat functionality
   - Communicates with backend via REST API (`/api/query`, `/api/courses`)

2. **API Layer** (`backend/app.py`)
   - FastAPI server with CORS and trusted host middleware
   - Request validation using Pydantic models
   - Session management and error handling
   - Serves static files and API documentation

3. **RAG Orchestration** (`backend/rag_system.py`)
   - Central coordinator for all backend components
   - Manages query processing pipeline: Session → AI → Tools → Response
   - Handles course document loading and analytics

4. **AI Generation** (`backend/ai_generator.py`)
   - Anthropic Claude API integration with tool support
   - System prompt configured for educational content
   - Temperature 0, max 800 tokens, supports search tools

5. **Search & Retrieval**
   - `search_tools.py`: CourseSearchTool for Claude to query vector store
   - `vector_store.py`: ChromaDB integration with semantic search
   - `document_processor.py`: Text chunking and course structure parsing

6. **Data Management**
   - `models.py`: Pydantic models (Course, Lesson, CourseChunk)
   - `session_manager.py`: Conversation history tracking
   - `config.py`: Centralized configuration with dataclass

### Document Processing Pipeline
Documents must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: [lesson title]
Lesson Link: [lesson url]
[lesson content...]
```

Processing steps:
1. Parse metadata from first 3 lines
2. Split content by lesson markers (`Lesson N:`)
3. Chunk text using sentence boundaries (800 chars, 100 overlap)
4. Add contextual prefixes: `"Course {title} Lesson {number} content: {chunk}"`
5. Store in ChromaDB with embeddings

### Query Processing Flow
1. Frontend sends POST to `/api/query` with query and session_id
2. RAG system retrieves conversation history
3. Claude API called with search tools available
4. If needed, CourseSearchTool queries ChromaDB for relevant chunks
5. Claude generates response using search results
6. Sources collected and conversation history updated
7. Response returned with answer, sources, and session_id

## Configuration

Key settings in `backend/config.py`:
- `CHUNK_SIZE: 800` - Text chunk size for vector storage
- `CHUNK_OVERLAP: 100` - Character overlap between chunks
- `MAX_RESULTS: 5` - Maximum search results returned
- `MAX_HISTORY: 2` - Conversation messages remembered
- `ANTHROPIC_MODEL: "claude-sonnet-4-20250514"`
- `EMBEDDING_MODEL: "all-MiniLM-L6-v2"`

## File Structure Context

- `/docs/` - Course script files (course1_script.txt, etc.)
- `/backend/chroma_db/` - ChromaDB persistence directory
- `/frontend/` - Static web files served by FastAPI
- `run.sh` - Startup script that creates docs directory and starts server
- `pyproject.toml` - uv dependency management (no test framework configured)

## Important Implementation Details

### Vector Store Initialization
The system automatically loads documents from `/docs` folder on startup. Documents are processed once and stored persistently in ChromaDB. Existing courses are not reprocessed.

### Session Management
Each user gets a unique session_id for conversation continuity. Sessions store up to 2 previous exchanges (MAX_HISTORY). New sessions auto-generate IDs.

### Tool Integration
Claude has access to CourseSearchTool which performs semantic search over course chunks. The tool returns relevant content that Claude synthesizes into educational responses.

### Error Handling
- UTF-8 encoding with fallback for document reading
- Graceful handling of missing documents or API failures
- Frontend displays loading states and error messages

### CORS Configuration
The FastAPI server allows all origins (`*`) for development, with comprehensive CORS headers for proxy compatibility.

## Windows Compatibility Note
Use Git Bash to run commands on Windows systems as specified in README.md.
- Use uv to run all Python files