"""
Search API - Hybrid vector search endpoint
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Literal, List

router = APIRouter()


class SearchRequest(BaseModel):
    """Search request model."""
    query: str
    role: Literal["dispatcher", "commander", "public"] = "dispatcher"
    collection: Literal["incidents", "protocols", "visual", "landmarks"] = "incidents"
    top_k: int = 10
    use_sparse: bool = True  # Enable hybrid search


class SearchResult(BaseModel):
    """Individual search result."""
    id: str
    score: float
    payload: dict


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    collection: str
    results: List[SearchResult]
    total: int
    hybrid_mode: bool


@router.post("/", response_model=SearchResponse)
async def search(request: Request, search_req: SearchRequest):
    """
    Perform hybrid search (dense + sparse) on Qdrant collections.
    
    Features:
    - Dense semantic search via FastEmbed
    - Sparse keyword matching via BM25/SPLADE
    - RRF fusion for combined ranking
    - RBAC filtering based on user role
    """
    qdrant_service = request.app.state.qdrant
    
    # TODO: Replace with actual hybrid search implementation
    # This is a stub for infrastructure testing
    
    stub_results = [
        SearchResult(
            id="doc-001",
            score=0.92,
            payload={
                "content": f"Sample result for query: {search_req.query[:50]}",
                "type": "incident",
                "access_level": "dispatcher",
            }
        ),
        SearchResult(
            id="doc-002", 
            score=0.85,
            payload={
                "content": "Another relevant document...",
                "type": "protocol",
                "access_level": "public",
            }
        ),
    ]
    
    return SearchResponse(
        query=search_req.query,
        collection=search_req.collection,
        results=stub_results,
        total=len(stub_results),
        hybrid_mode=search_req.use_sparse,
    )


@router.post("/visual")
async def visual_search(request: Request, query: str, top_k: int = 5):
    """
    Search visual evidence collection using text query.
    Uses CLIP to embed text and search image embeddings.
    """
    # TODO: CLIP text embedding + Qdrant visual_evidence search
    return {
        "query": query,
        "collection": "visual_evidence",
        "results": [],
        "message": "Visual search not yet implemented",
    }


@router.post("/landmarks")
async def landmark_search(
    request: Request,
    query: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 2.0,
):
    """
    Search landmark database with optional geo-radius filtering.
    """
    # TODO: Geo-filtered landmark search
    return {
        "query": query,
        "collection": "landmark_index",
        "geo_filter": {"lat": lat, "lon": lon, "radius_km": radius_km} if lat else None,
        "results": [],
        "message": "Landmark search not yet implemented",
    }
