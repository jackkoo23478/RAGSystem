# Enterprise Document RAG System

A full-stack RAG application for enterprise document search and question answering, with authentication, role-based access control, document upload, vector search, source citations, and an admin dashboard.

## Features
- User login and role-based access control
- Admin document upload and ingestion
- PDF/TXT parsing, chunking, embeddings, and vector indexing
- Retrieval-augmented question answering
- Source citations in every answer
- Admin dashboard with document and query metrics
- Basic logging and error handling

## Demo
- Screenshots: `docs/`
- Demo video: [add link]
- Live demo: [optional]

## Tech Stack
- Frontend: Next.js / React
- Backend: Node.js / Python / API routes
- Auth: NextAuth / JWT
- Embeddings: OpenAI / Hugging Face
- Vector Store: FAISS / Chroma / pgvector
- Database: PostgreSQL / SQLite
- Styling: Tailwind CSS

## Architecture
[Put system diagram here]

Flow:
1. Admin uploads a document
2. System extracts text and splits into chunks
3. Chunks are converted to embeddings
4. Embeddings are stored in vector DB
5. User asks a question
6. System retrieves relevant chunks
7. LLM generates answer with citations

## Screenshots
- Login page
- Upload page
- Chat with citations
- Admin dashboard

## Setup
### Prerequisites
- Node.js xx / Python xx
- API key
- Database

### Installation
```bash
git clone ...
cd enterprise-rag-system
npm install
cp .env.example .env
npm run dev
```

## Environment Variables
```env
OPENAI_API_KEY=
DATABASE_URL=
NEXTAUTH_SECRET=
```

## Usage
- Login as admin to upload documents
- Wait for ingestion to complete
- Login as user to ask questions
- Check citations below each answer

## Example Queries
- What is the refund policy?
- Summarize the onboarding process.
- What are the security requirements?

## Error Handling
- Unsupported file type
- Failed extraction
- Empty retrieval results
- API timeout / embedding failure

## Limitations
- Supports only PDF/TXT in MVP
- Single-organization setup
- Basic dashboard only
- No reranking in current version

## Roadmap
- DOCX support
- Query history
- Feedback buttons
- Reranking
- Docker deployment

## Author
Koo Jack

## License
MIT