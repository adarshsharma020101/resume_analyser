"""
Local vector store using ChromaDB + Ollama embeddings.
No external embedding APIs — all embeddings generated locally via Ollama.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)

_chroma_client: Optional[chromadb.AsyncHttpClient] = None


async def get_chroma_client() -> chromadb.AsyncHttpClient:
    """Lazy-init and return the ChromaDB async HTTP client."""
    global _chroma_client
    if _chroma_client is None:
        host = settings.__dict__.get("CHROMA_HOST", "http://chromadb:8000")
        # Parse host/port from URL
        import re
        m = re.match(r"https?://([^:/]+)(?::(\d+))?", host)
        chroma_host = m.group(1) if m else "chromadb"
        chroma_port = int(m.group(2)) if m and m.group(2) else 8000

        auth_token = settings.__dict__.get("CHROMA_AUTH_TOKEN", "")
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

        _chroma_client = await chromadb.AsyncHttpClient(
            host=chroma_host,
            port=chroma_port,
            headers=headers,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


async def get_ollama_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """Generate embedding using local Ollama. Returns float list."""
    import httpx
    embed_model = model or settings.OLLAMA_EMBED_MODEL
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json={"model": embed_model, "prompt": text})
        resp.raise_for_status()
        data = resp.json()
        return data.get("embedding", [])


async def upsert_document_embedding(
    collection_name: str,
    doc_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    embed_model: Optional[str] = None,
) -> None:
    """Embed a document and upsert it into the specified ChromaDB collection."""
    try:
        client = await get_chroma_client()
        collection = await client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        embedding = await get_ollama_embedding(text[:8000], embed_model)
        await collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text[:10000]],
            metadatas=[metadata or {}],
        )
        log.debug("Upserted embedding for doc_id=%s in collection=%s", doc_id, collection_name)
    except Exception as e:
        log.warning("Vector store upsert failed for %s: %s", doc_id, e)


async def query_similar(
    collection_name: str,
    query_text: str,
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None,
    embed_model: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for documents similar to query_text.
    Returns list of {id, text, metadata, distance}.
    """
    try:
        client = await get_chroma_client()
        collection = await client.get_or_create_collection(name=collection_name)
        embedding = await get_ollama_embedding(query_text[:8000], embed_model)
        results = await collection.query(
            query_embeddings=[embedding],
            n_results=min(n_results, 100),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        output: List[Dict[str, Any]] = []
        ids = (results.get("ids") or [[]])[0]
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]
        for i, doc_id in enumerate(ids):
            output.append({
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else 1.0,
                "similarity": 1.0 - (dists[i] if i < len(dists) else 1.0),
            })
        return output
    except Exception as e:
        log.warning("Vector store query failed: %s", e)
        return []


async def delete_document_embedding(collection_name: str, doc_id: str) -> None:
    """Remove a document embedding from ChromaDB."""
    try:
        client = await get_chroma_client()
        collection = await client.get_or_create_collection(name=collection_name)
        await collection.delete(ids=[doc_id])
    except Exception as e:
        log.warning("Vector store delete failed for %s: %s", doc_id, e)


async def delete_user_embeddings(user_id: str) -> None:
    """Remove all embeddings for a user across all collections."""
    for collection_name in [
        settings.CHROMA_COLLECTION_RESUMES,
        settings.CHROMA_COLLECTION_JOBS,
        settings.CHROMA_COLLECTION_LINKEDIN,
    ]:
        try:
            client = await get_chroma_client()
            collection = await client.get_or_create_collection(name=collection_name)
            await collection.delete(where={"user_id": user_id})
            log.info("Deleted embeddings for user=%s from collection=%s", user_id, collection_name)
        except Exception as e:
            log.warning("Failed to delete embeddings for user=%s collection=%s: %s", user_id, collection_name, e)
