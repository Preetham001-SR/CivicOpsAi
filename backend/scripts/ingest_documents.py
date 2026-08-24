#!/usr/bin/env python3
"""
CLI script for ingesting documents into the RAG system.
Usage:
    python -m scripts.ingest_documents --source municipal_code --dir ./data/municipal_code
    python -m scripts.ingest_documents --source past_incident --dir ./data/incidents --category pothole
    python -m scripts.ingest_documents --file ./data/sop.txt --source policy_document --title "Street Maintenance SOP"
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional
import structlog

from app.rag.ingestion import DocumentIngestor, ChunkConfig
from app.db.models import ComplaintCategory

logger = structlog.get_logger()


CATEGORY_MAP = {
    "pothole": ComplaintCategory.POTHOLE,
    "broken_sign": ComplaintCategory.BROKEN_SIGN,
    "damaged_property": ComplaintCategory.DAMAGED_PROPERTY,
    "graffiti": ComplaintCategory.GRAFFITI,
    "streetlight_outage": ComplaintCategory.STREETLIGHT_OUTAGE,
    "sidewalk_damage": ComplaintCategory.SIDEWALK_DAMAGE,
    "traffic_signal": ComplaintCategory.TRAFFIC_SIGNAL,
    "drainage_issue": ComplaintCategory.DRAINAGE_ISSUE,
    "other": ComplaintCategory.OTHER,
}


async def ingest_directory(
    directory: Path,
    source: str,
    category: Optional[ComplaintCategory] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    file_pattern: str = "*.txt",
    category_map: Optional[dict] = None,
):
    config = ChunkConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    ingestor = DocumentIngestor(config=config)
    
    print(f"Ingesting from {directory} (source: {source})")
    print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    print(f"File pattern: {file_pattern}")
    if category:
        print(f"Category filter: {category.value}")
    if category_map:
        print(f"Category map: {category_map}")
    print("-" * 60)
    
    results = await ingestor.ingest_directory(
        directory=directory,
        source=source,
        category_map=category_map,
        file_pattern=file_pattern,
    )
    
    total_chunks = 0
    for result in results:
        status = "✓" if result.chunks_created > 0 else "✗"
        cat_str = f" [{result.category.value}]" if result.category else ""
        print(f"{status} {result.title}{cat_str} - {result.chunks_created} chunks (doc_id: {result.document_id})")
        total_chunks += result.chunks_created
    
    print("-" * 60)
    print(f"Total: {len(results)} files, {total_chunks} chunks ingested")
    
    return results


async def ingest_single_file(
    file_path: Path,
    source: str,
    title: str,
    category: Optional[ComplaintCategory] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
):
    config = ChunkConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    ingestor = DocumentIngestor(config=config)
    
    print(f"Ingesting file: {file_path}")
    print(f"Title: {title}, Source: {source}")
    if category:
        print(f"Category: {category.value}")
    print("-" * 60)
    
    result = await ingestor.ingest_file(
        file_path=file_path,
        title=title,
        source=source,
        category=category,
    )
    
    status = "✓" if result.chunks_created > 0 else "✗"
    print(f"{status} {result.title} - {result.chunks_created} chunks (doc_id: {result.document_id})")
    print("-" * 60)
    print(f"Total: 1 file, {result.chunks_created} chunks ingested")
    
    return result


def parse_category(category_str: Optional[str]) -> Optional[ComplaintCategory]:
    if not category_str:
        return None
    category_str = category_str.lower()
    if category_str in CATEGORY_MAP:
        return CATEGORY_MAP[category_str]
    raise ValueError(f"Unknown category: {category_str}. Valid: {list(CATEGORY_MAP.keys())}")


def build_category_map(args) -> Optional[dict]:
    if not args.category_map:
        return None
    
    mapping = {}
    for item in args.category_map:
        if "=" not in item:
            raise ValueError(f"Invalid category map format: {item}. Use pattern=category")
        pattern, cat_str = item.split("=", 1)
        category = parse_category(cat_str)
        mapping[pattern] = category
    
    return mapping


async def main():
    parser = argparse.ArgumentParser(description="Ingest documents into CivicOps RAG system")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    dir_parser = subparsers.add_parser("directory", help="Ingest all files in a directory")
    dir_parser.add_argument("--dir", "-d", required=True, help="Directory path")
    dir_parser.add_argument("--source", "-s", required=True, help="Document source (e.g., municipal_code, past_incident, policy_document)")
    dir_parser.add_argument("--category", "-c", help="Default category for all files")
    dir_parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size in characters")
    dir_parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap in characters")
    dir_parser.add_argument("--pattern", default="*.txt", help="File glob pattern")
    dir_parser.add_argument("--category-map", action="append", help="Map filename pattern to category (e.g., 'pothole=pothole')")
    
    file_parser = subparsers.add_parser("file", help="Ingest a single file")
    file_parser.add_argument("--file", "-f", required=True, help="File path")
    file_parser.add_argument("--source", "-s", required=True, help="Document source")
    file_parser.add_argument("--title", "-t", required=True, help="Document title")
    file_parser.add_argument("--category", "-c", help="Category")
    file_parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size in characters")
    file_parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap in characters")
    
    args = parser.parse_args()
    
    try:
        if args.command == "directory":
            directory = Path(args.dir)
            if not directory.exists():
                print(f"Error: Directory not found: {directory}")
                sys.exit(1)
            
            category = parse_category(args.category) if args.category else None
            category_map = build_category_map(args)
            
            await ingest_directory(
                directory=directory,
                source=args.source,
                category=category,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                file_pattern=args.pattern,
                category_map=category_map,
            )
            
        elif args.command == "file":
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                sys.exit(1)
            
            category = parse_category(args.category) if args.category else None
            
            await ingest_single_file(
                file_path=file_path,
                source=args.source,
                title=args.title,
                category=category,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
        
        print("\nIngestion complete!")
        
    except Exception as e:
        logger.error("ingestion_failed", error=str(e))
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())