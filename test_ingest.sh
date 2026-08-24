#!/bin/bash
cd /Users/apple/CivicOps\ AI

# Create a temporary Python script
cat > /tmp/test_ingest.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/app')

from app.rag.ingestion import DocumentIngestor, ChunkConfig
from pathlib import Path

async def test():
    config = ChunkConfig(chunk_size=512, chunk_overlap=50)
    ingestor = DocumentIngestor(config=config)
    result = await ingestor.ingest_file(
        file_path=Path("/app/data/municipal_code/street_maintenance.txt"),
        title="street_maintenance",
        source="municipal_code",
    )
    print(f"Result: {result}")

asyncio.run(test())
EOF

docker run --rm --network civicopsai_default \
  -v /Users/apple/CivicOps\ AI/backend:/app \
  -w /app \
  python:3.11-slim \
  bash -c "
    pip install -q sentence-transformers langchain-huggingface langchain-text-splitters asyncpg pgvector sqlalchemy greenlet 2>&1 | tail -5
    python3 /tmp/test_ingest.py
  " 2>&1