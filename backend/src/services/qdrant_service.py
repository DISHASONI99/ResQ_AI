"""
Qdrant Service - Vector database operations with Qdrant Cloud
"""
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, SparseVectorParams
from typing import Optional, List, Dict, Any

from src.config import settings
from src.utils.logging import db, success, error, info


class QdrantService:
    """
    Qdrant vector database service.
    Handles collection management, upserts, and hybrid search.
    """
    
    def __init__(self):
        """Initialize Qdrant client with Cloud credentials."""
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            timeout=30,
        )
        
        # Collection configurations
        self.collections = {
            "incident_memory": {
                "dense_dim": 768,
                "sparse": True,
                "quantization": True,
            },
            "visual_evidence": {
                "dense_dim": 512,
                "sparse": False,
                "quantization": True,
            },
            "protocols_sops": {
                "dense_dim": 768,
                "sparse": False,
                "quantization": False,
            },
            "landmark_index": {
                "dense_dim": 768,
                "sparse": True,
                "quantization": False,
            },
            "semantic_cache": {
                "dense_dim": 768,
                "sparse": False,
                "quantization": False,
            },
        }
    
    async def initialize(self):
        """Initialize all collections on startup."""
        info("Initializing Qdrant collections...")
        
        existing = {c.name for c in self.client.get_collections().collections}
        
        for name, config in self.collections.items():
            if name not in existing:
                await self._create_collection(name, config)
                success(f"Created collection: {name}")
            else:
                info(f"Collection exists: {name}")
    
    async def _create_collection(self, name: str, config: dict):
        """Create a single collection with specified configuration."""
        vectors_config = {
            "dense": VectorParams(
                size=config["dense_dim"],
                distance=Distance.COSINE,
            )
        }
        
        sparse_vectors_config = None
        if config.get("sparse"):
            sparse_vectors_config = {
                "sparse": SparseVectorParams()
            }
        
        quantization_config = None
        if config.get("quantization"):
            quantization_config = models.BinaryQuantization(
                binary=models.BinaryQuantizationConfig(always_ram=True)
            )
        
        self.client.create_collection(
            collection_name=name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config,
            quantization_config=quantization_config,
        )
    
    async def hybrid_search(
        self,
        collection: str,
        dense_vector: List[float],
        sparse_vector: Optional[Dict[int, float]] = None,
        filter_conditions: Optional[dict] = None,
        top_k: int = 10,
    ) -> List[dict]:
        """
        Perform hybrid search (dense + sparse) with RRF fusion.
        
        Args:
            collection: Collection name
            dense_vector: Dense embedding vector
            sparse_vector: Sparse vector as {index: value} dict
            filter_conditions: Qdrant filter for RBAC
            top_k: Number of results to return
        """
        # Build filter
        qdrant_filter = None
        if filter_conditions:
            qdrant_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key=k,
                        match=models.MatchAny(any=v) if isinstance(v, list) else models.MatchValue(value=v)
                    )
                    for k, v in filter_conditions.items()
                ]
            )
        
        # If sparse vector provided and collection supports it
        if sparse_vector and self.collections.get(collection, {}).get("sparse"):
            # Hybrid search with prefetch - filter applied to each prefetch
            results = self.client.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                        query=dense_vector,
                        using="dense",
                        limit=top_k * 2,
                        filter=qdrant_filter,
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=list(sparse_vector.keys()),
                            values=list(sparse_vector.values()),
                        ),
                        using="sparse",
                        limit=top_k * 2,
                        filter=qdrant_filter,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
            )
            
            return [
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload,
                }
                for point in results.points
            ]
        else:
            # Dense-only search - try named vector first, then regular
            try:
                # Try named vector (for collections created by this service)
                results = self.client.query_points(
                    collection_name=collection,
                    query=dense_vector,
                    using="dense",
                    limit=top_k,
                )
            except Exception as e:
                # Fall back to regular vector (for collections from seed script)
                error_str = str(e).lower()
                if "multi" in error_str or "conversion" in error_str or "vector name" in error_str:
                    results = self.client.query_points(
                        collection_name=collection,
                        query=dense_vector,
                        limit=top_k,
                    )
                else:
                    raise e
            
            return [
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload,
                }
                for point in results.points
            ]
    
    async def upsert(
        self,
        collection: str,
        id: str,
        dense_vector: List[float],
        payload: dict,
        sparse_vector: Optional[Dict[int, float]] = None,
    ):
        """Upsert a document with vectors and payload."""
        vectors = {"dense": dense_vector}
        
        if sparse_vector and self.collections.get(collection, {}).get("sparse"):
            vectors["sparse"] = models.SparseVector(
                indices=list(sparse_vector.keys()),
                values=list(sparse_vector.values()),
            )
        
        self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=id,
                    vector=vectors,
                    payload=payload,
                )
            ],
        )
    
    async def get_collection_info(self, collection: str) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(collection)
        return {
            "name": collection,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status.name,
        }
