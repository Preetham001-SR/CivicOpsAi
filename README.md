# CivicOps AI

Multi-agent pipeline for processing citizen infrastructure complaints using LangGraph, FastAPI, and multimodal AI.

## Architecture

```
User Report → Intake Agent
  → Vision Agent + Speech Agent + Location Agent (parallel)
    → RAG Agent (retrieves city rules / past incidents, cites sources)
      → Decision Agent (classification, priority, recommended action)
        → Verification Agent (checks decision against evidence, produces confidence score)
          → Human Review (only if confidence < threshold)
            → Work Order (final structured output)
```

## Confidence Routing

- **> 90%** → Auto-process
- **70–90%** → Queue for optional review
- **< 70%** → Mandatory human review before work order is finalized

## Tech Stack

- **Backend**: Python + FastAPI
- **Orchestration**: LangGraph + LangChain
- **RAG Store**: PostgreSQL + pgvector
- **Cache/Queue**: Redis + Celery
- **AI Models**: Hugging Face (vision/speech/embeddings) + Anthropic Claude (reasoning)
- **File Storage**: S3-compatible (MinIO in dev)
- **Observability**: Langfuse + OpenTelemetry
- **Metrics**: Prometheus + Grafana
- **Containerization**: Docker + docker-compose
- **CI**: GitHub Actions

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Anthropic API key
- Langfuse account (optional, for observability)

### Development Setup

1. **Clone and configure**
   ```bash
   git clone <repo>
   cd civicops-ai
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Access services**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - Tempo: http://localhost:3200

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://civicops:civicops@localhost:5432/civicops
export REDIS_URL=redis://localhost:6379/0
export ANTHROPIC_API_KEY=your_key
# ... other vars from .env.example

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload

# Start worker (in another terminal)
celery -A app.workers.celery_app worker --loglevel=INFO
```

## API Usage

### Submit a Complaint

```bash
curl -X POST http://localhost:8000/api/v1/complaints \
  -H "Content-Type: application/json" \
  -d '{
    "text_description": "Large pothole on Main Street near Oak Ave",
    "photo_url": "https://example.com/photo.jpg",
    "audio_url": "https://example.com/audio.wav",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "address": "Main St & Oak Ave, New York, NY"
  }'
```

### Check Complaint Status

```bash
curl http://localhost:8000/api/v1/complaints/{complaint_id}
```

### View Agent Logs

```bash
curl http://localhost:8000/api/v1/complaints/{complaint_id}/logs
```

### Submit Human Review

```bash
curl -X POST http://localhost:8000/api/v1/complaints/{complaint_id}/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_id": "reviewer-001",
    "decision": "approve",
    "notes": "Verified on site"
  }'
```

## Project Structure

```
civicops-ai/
├── app/
│   ├── api/              # FastAPI routes
│   ├── agents/           # LangGraph agents
│   │   ├── base.py       # Base agent class
│   │   ├── intake.py     # Input validation & file handling
│   │   ├── vision.py     # Image analysis (HF ViT)
│   │   ├── speech.py     # Audio transcription (Whisper)
│   │   ├── location.py   # Geocoding & jurisdiction
│   │   ├── rag.py        # RAG with pgvector
│   │   ├── decision.py   # Classification & priority (Claude)
│   │   ├── verification.py # Confidence scoring
│   │   ├── work_order.py # Work order generation
│   │   ├── pipeline.py   # LangGraph workflow
│   │   └── state.py      # Pipeline state types
│   ├── core/             # Config, observability
│   ├── db/               # Database models & session
│   ├── schemas/          # Pydantic models
│   ├── services/         # External services (MinIO)
│   └── workers/          # Celery tasks
├── tests/
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── alembic/              # DB migrations
├── monitoring/           # Observability configs
├── scripts/              # Utility scripts
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.worker
├── requirements.txt
├── pytest.ini
└── .env.example
```

## Running Tests

```bash
# Unit tests
pytest tests/unit -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

## Adding RAG Documents

```python
from app.db.session import AsyncSessionLocal
from app.db.models import RagDocument, ComplaintCategory

async def add_document():
    async with AsyncSessionLocal() as db:
        doc = RagDocument(
            title="Pothole Repair Standards",
            content="Potholes exceeding 25cm...",
            embedding=[0.1] * 384,  # Generate with sentence-transformers
            source="municipal_code",
            category=ComplaintCategory.POTHOLE,
        )
        db.add(doc)
        await db.commit()
```

## Environment Variables

See `.env.example` for all required variables.

Key variables:
- `ANTHROPIC_API_KEY` - Required for Decision/Verification agents
- `DATABASE_URL` - PostgreSQL with pgvector
- `REDIS_URL` - For Celery queue
- `LANGFUSE_*` - For observability (optional)
- `MINIO_*` - For file storage

## License

MIT