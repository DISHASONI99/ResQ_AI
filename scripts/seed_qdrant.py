#!/usr/bin/env python3
"""
Qdrant Seeding Script - Push data to Qdrant Cloud collections

This script:
1. Reads downloaded/generated data from data/ directory
2. Reads disaster images from Disaster_Dataset/ (manual download)
3. Generates embeddings using FastEmbed/SPLADE (text) and CLIP (images)
4. Upserts to Qdrant Cloud with detailed logging

Run after download_data.py and before starting the application.

IMPORTANT: Once seeded, Qdrant Cloud stores embeddings permanently.
You don't need to re-run this script unless you change Qdrant clusters.
"""
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# ============ CONFIGURATION ============
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = PROJECT_ROOT / "Disaster_Dataset"  # Disaster images in ResQ_AI/Disaster_Dataset/

load_dotenv(PROJECT_ROOT / ".env")


# ============ LOGGING ============
class Logger:
    """Detailed logging with colors and timestamps."""
    
    COLORS = {
        "INFO": "\033[94m",      # Blue
        "SUCCESS": "\033[92m",   # Green
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "DB": "\033[96m",        # Cyan (for database operations)
        "EMBED": "\033[95m",     # Magenta (for embeddings)
        "RESET": "\033[0m",
    }
    
    @staticmethod
    def log(level: str, message: str, indent: int = 0):
        color = Logger.COLORS.get(level, "")
        reset = Logger.COLORS["RESET"]
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        prefix = "  " * indent
        print(f"{color}[{timestamp}] [{level:7}] {prefix}{message}{reset}")
    
    @staticmethod
    def info(msg, indent=0): Logger.log("INFO", msg, indent)
    
    @staticmethod
    def success(msg, indent=0): Logger.log("SUCCESS", msg, indent)
    
    @staticmethod
    def warning(msg, indent=0): Logger.log("WARNING", msg, indent)
    
    @staticmethod
    def error(msg, indent=0): Logger.log("ERROR", msg, indent)
    
    @staticmethod
    def db(msg, indent=0): Logger.log("DB", msg, indent)
    
    @staticmethod
    def embed(msg, indent=0): Logger.log("EMBED", msg, indent)


log = Logger()


def check_qdrant_connection():
    """Verify Qdrant Cloud connection."""
    from qdrant_client import QdrantClient
    
    url = os.getenv("QDRANT_URL", "")
    api_key = os.getenv("QDRANT_API_KEY", "")
    
    if not url or "your-cluster" in url:
        log.error("❌ QDRANT_URL not set in .env file!")
        log.info("Please set QDRANT_URL=https://your-cluster.gcp.cloud.qdrant.io:6333", indent=1)
        return None
    
    if not api_key or api_key == "your-qdrant-api-key-here":
        log.error("❌ QDRANT_API_KEY not set in .env file!")
        log.info("Get your API key from https://cloud.qdrant.io", indent=1)
        return None
    
    log.db(f"Connecting to Qdrant: {url[:50]}...")
    
    try:
        client = QdrantClient(url=url, api_key=api_key, timeout=30)
        collections = client.get_collections()
        log.success(f"✅ Connected to Qdrant Cloud!")
        log.db(f"   Existing collections: {[c.name for c in collections.collections]}", indent=1)
        return client
    except Exception as e:
        log.error(f"❌ Failed to connect: {e}")
        return None


def delete_all_collections(client):
    """Delete all existing collections to free up Qdrant Cloud storage."""
    log.info("🗑️ Cleaning up existing collections (to avoid storage limits)...")
    
    try:
        existing = client.get_collections().collections
        
        if not existing:
            log.info("  No existing collections to delete", indent=1)
            return
        
        for collection in existing:
            log.db(f"  Deleting: {collection.name}...", indent=1)
            client.delete_collection(collection.name)
        
        log.success(f"✅ Deleted {len(existing)} collections", indent=1)
    except Exception as e:
        log.warning(f"⚠️ Failed to delete some collections: {e}")


def create_collections(client):
    """Create Qdrant collections if they don't exist."""
    from qdrant_client.models import Distance, VectorParams, SparseVectorParams, BinaryQuantization, BinaryQuantizationConfig
    
    collections_config = {
        "incident_memory": {"dense_dim": 768, "sparse": True, "quantization": True},
        "visual_evidence": {"dense_dim": 512, "sparse": False, "quantization": True},
        "protocols_sops": {"dense_dim": 768, "sparse": False, "quantization": False},
        "landmark_index": {"dense_dim": 768, "sparse": True, "quantization": False},
        "semantic_cache": {"dense_dim": 768, "sparse": False, "quantization": False},
    }
    
    existing = {c.name for c in client.get_collections().collections}
    
    for name, config in collections_config.items():
        if name in existing:
            log.db(f"✓ Collection exists: {name}", indent=1)
            continue
        
        log.db(f"Creating collection: {name}...", indent=1)
        
        vectors_config = {
            "dense": VectorParams(size=config["dense_dim"], distance=Distance.COSINE)
        }
        
        sparse_config = None
        if config.get("sparse"):
            sparse_config = {"sparse": SparseVectorParams()}
        
        quant_config = None
        if config.get("quantization"):
            quant_config = BinaryQuantization(binary=BinaryQuantizationConfig(always_ram=True))
        
        client.create_collection(
            collection_name=name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_config,
            quantization_config=quant_config,
        )
        
        log.success(f"✅ Created: {name} (dim={config['dense_dim']}, sparse={config.get('sparse', False)})", indent=2)
    
    return True


def load_text_embedding_model():
    """Load FastEmbed text model."""
    log.embed("Loading FastEmbed model: BAAI/bge-base-en-v1.5...")
    
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding("BAAI/bge-base-en-v1.5")
        
        # Warm up with test embedding
        test_emb = list(model.embed(["test"]))[0]
        log.success(f"✅ FastEmbed loaded! Output dim: {len(test_emb)}")
        return model
    except Exception as e:
        log.error(f"❌ Failed to load FastEmbed: {e}")
        return None


def load_sparse_model():
    """Load SPLADE sparse model."""
    log.embed("Loading SPLADE sparse model...")
    
    try:
        from fastembed import SparseTextEmbedding
        model = SparseTextEmbedding("prithivida/Splade_PP_en_v1")
        
        # Warm up
        test_sparse = list(model.embed(["test"]))[0]
        log.success(f"✅ SPLADE loaded! Non-zero terms: {len(test_sparse.indices)}")
        return model
    except Exception as e:
        log.warning(f"⚠️ SPLADE not available: {e}")
        return None


def load_clip_model():
    """Load CLIP model for image embeddings."""
    log.embed("Loading CLIP model: openai/clip-vit-base-patch32...")
    
    try:
        from transformers import CLIPModel, CLIPProcessor
        import torch
        
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        log.success(f"✅ CLIP loaded! Output dim: 512")
        return model, processor
    except Exception as e:
        log.warning(f"⚠️ CLIP not available: {e}")
        return None, None


def seed_incidents(client, text_model, sparse_model):
    """Seed incident_memory collection."""
    from qdrant_client.models import PointStruct, SparseVector
    
    incidents_file = DATA_DIR / "synthetic" / "incidents.json"
    
    if not incidents_file.exists():
        log.warning(f"⚠️ No incidents file found at {incidents_file}")
        log.info("Run download_data.py first to generate synthetic data", indent=1)
        return 0
    
    with open(incidents_file) as f:
        incidents = json.load(f)
    
    log.db(f"Seeding {len(incidents)} incidents to incident_memory...")
    
    points = []
    for i, incident in enumerate(incidents):
        # Generate embedding
        text = f"{incident['description']} {incident['type']} {incident['location']['name']}"
        
        log.embed(f"  [{i+1}/{len(incidents)}] Embedding: {text[:50]}...", indent=1)
        
        dense_emb = list(text_model.embed([text]))[0].tolist()
        
        vectors = {"dense": dense_emb}
        
        if sparse_model:
            sparse_emb = list(sparse_model.embed([text]))[0]
            vectors["sparse"] = SparseVector(
                indices=sparse_emb.indices.tolist(),
                values=sparse_emb.values.tolist(),
            )
        
        point = PointStruct(
            id=i,
            vector=vectors,
            payload={
                "incident_id": incident["id"],
                "type": incident["type"],
                "priority": incident["priority"],
                "description": incident["description"],
                "location": incident["location"],
                "status": incident["status"],
                "access_level": incident["access_level"],
            }
        )
        points.append(point)
    
    # Batch upsert
    log.db(f"  Upserting {len(points)} points to Qdrant...", indent=1)
    
    start = time.time()
    client.upsert(collection_name="incident_memory", points=points)
    elapsed = time.time() - start
    
    log.success(f"✅ Upserted {len(points)} incidents in {elapsed:.2f}s", indent=1)
    
    # Verify
    info = client.get_collection("incident_memory")
    log.db(f"  Collection now has {info.points_count} points", indent=1)
    
    return len(points)


def seed_sops(client, text_model):
    """Seed protocols_sops collection from JSON SOP files."""
    from qdrant_client.models import PointStruct
    
    sops_dir = DATA_DIR / "synthetic" / "sops"
    
    # Find all JSON SOP files (new format)
    json_files = list(sops_dir.glob("emergency_sop*.json"))
    
    if not json_files:
        log.warning(f"⚠️ No SOP JSON files found in {sops_dir}")
        return 0
    
    log.db(f"Found {len(json_files)} SOP JSON files")
    
    all_sops = []
    
    # Parse each JSON file
    for json_file in json_files:
        log.info(f"  Reading: {json_file.name}", indent=1)
        with open(json_file) as f:
            data = json.load(f)
        
        # Extract SOPs from different sections in the JSON
        # Handle fire_emergency_sops, medical_emergency_sops, etc.
        for key in data:
            if key.endswith("_sops") and isinstance(data[key], list):
                for sop in data[key]:
                    all_sops.append({
                        "sop_id": sop.get("sop_id", f"SOP-{len(all_sops)+1:03d}"),
                        "title": sop.get("title", "Unknown SOP"),
                        "category": sop.get("category", key.replace("_sops", "").replace("_", " ").title()),
                        "subcategory": sop.get("subcategory", ""),
                        "keywords": sop.get("keywords", []),
                        "priority_determination": sop.get("priority_determination", {}),
                        "required_assets": sop.get("required_assets", {}),
                        "response_protocol_steps": sop.get("response_protocol_steps", []),
                        "escalation_triggers": sop.get("escalation_triggers", []),
                        "india_specific_considerations": sop.get("india_specific_considerations", []),
                        "source_file": json_file.name,
                    })
        
        # Also include priority_classification and system_metadata as reference docs
        if "priority_classification" in data:
            all_sops.append({
                "sop_id": "SOP-PRIORITY-001",
                "title": "Priority Classification Guidelines",
                "category": "Reference",
                "content": json.dumps(data["priority_classification"], indent=2),
                "source_file": json_file.name,
            })
        
        if "system_metadata" in data:
            all_sops.append({
                "sop_id": "SOP-META-001",
                "title": "Emergency Response System Metadata",
                "category": "Reference",
                "content": json.dumps(data["system_metadata"], indent=2),
                "source_file": json_file.name,
            })
    
    log.db(f"Seeding {len(all_sops)} SOPs to protocols_sops...")
    
    points = []
    for i, sop in enumerate(all_sops):
        # Build searchable text from SOP content
        text_parts = [sop.get("title", ""), sop.get("category", ""), sop.get("subcategory", "")]
        
        # Add keywords
        text_parts.extend(sop.get("keywords", []))
        
        # Add step summaries
        for step in sop.get("response_protocol_steps", []):
            if isinstance(step, dict):
                text_parts.append(step.get("phase", ""))
                text_parts.append(step.get("action", ""))
        
        # If it's a reference doc, use content directly
        if "content" in sop:
            text_parts.append(sop["content"][:1000])
        
        embed_text = " ".join(filter(None, text_parts))[:2000]
        
        log.embed(f"  [{i+1}/{len(all_sops)}] Embedding SOP: {sop.get('sop_id', 'Unknown')}", indent=1)
        
        dense_emb = list(text_model.embed([embed_text]))[0].tolist()
        
        point = PointStruct(
            id=i,
            vector={"dense": dense_emb},
            payload={
                "sop_id": sop.get("sop_id", f"SOP-{i:03d}"),
                "title": sop.get("title", ""),
                "category": sop.get("category", ""),
                "subcategory": sop.get("subcategory", ""),
                "keywords": sop.get("keywords", []),
                "required_assets": sop.get("required_assets", {}),
                "escalation_triggers": sop.get("escalation_triggers", []),
                "source_file": sop.get("source_file", ""),
            }
        )
        points.append(point)
    
    log.db(f"  Upserting {len(points)} SOPs to Qdrant...", indent=1)
    
    start = time.time()
    client.upsert(collection_name="protocols_sops", points=points)
    elapsed = time.time() - start
    
    log.success(f"✅ Upserted {len(points)} SOPs in {elapsed:.2f}s", indent=1)
    
    return len(points)


def seed_landmarks(client, text_model, sparse_model):
    """Seed landmark_index collection."""
    from qdrant_client.models import PointStruct, SparseVector
    
    landmarks_file = DATA_DIR / "osm" / "bangalore_landmarks.json"
    
    if not landmarks_file.exists():
        log.warning(f"⚠️ No landmarks file found at {landmarks_file}")
        return 0
    
    with open(landmarks_file) as f:
        landmarks = json.load(f)
    
    log.db(f"Seeding {len(landmarks)} landmarks to landmark_index...")
    
    points = []
    for i, landmark in enumerate(landmarks):
        # Combine name and alt names for better matching
        text = f"{landmark['name']} {' '.join(landmark.get('alt_names', []))}"
        
        log.embed(f"  [{i+1}/{len(landmarks)}] Embedding: {landmark['name']}", indent=1)
        
        dense_emb = list(text_model.embed([text]))[0].tolist()
        
        vectors = {"dense": dense_emb}
        
        if sparse_model:
            sparse_emb = list(sparse_model.embed([text]))[0]
            vectors["sparse"] = SparseVector(
                indices=sparse_emb.indices.tolist(),
                values=sparse_emb.values.tolist(),
            )
        
        point = PointStruct(
            id=i,
            vector=vectors,
            payload={
                "name": landmark["name"],
                "alt_names": landmark.get("alt_names", []),
                "type": landmark["type"],
                "lat": landmark["lat"],
                "lon": landmark["lon"],
            }
        )
        points.append(point)
    
    log.db(f"  Upserting {len(points)} landmarks to Qdrant...", indent=1)
    
    start = time.time()
    client.upsert(collection_name="landmark_index", points=points)
    elapsed = time.time() - start
    
    log.success(f"✅ Upserted {len(points)} landmarks in {elapsed:.2f}s", indent=1)
    
    return len(points)


def seed_images(client, clip_model, clip_processor):
    """Seed visual_evidence collection with disaster images."""
    from qdrant_client.models import PointStruct
    from PIL import Image
    import torch
    
    if clip_model is None:
        log.warning("⚠️ CLIP model not loaded, skipping image seeding")
        return 0
    
    if not IMAGES_DIR.exists():
        log.warning(f"⚠️ Disaster_Dataset not found at {IMAGES_DIR}")
        log.info("Expected location: ResQ_AI/Disaster_Dataset/", indent=1)
        return 0
    
    # Find images by category (20 per folder)
    images_to_process = []
    categories = [d for d in IMAGES_DIR.iterdir() if d.is_dir()]
    
    log.info(f"Found {len(categories)} categories in Disaster_Dataset")
    
    for category_dir in categories:
        category_images = []
        for ext in {".jpg", ".jpeg", ".png", ".webp"}:
            # Use recursive glob to find images in subfolders too (e.g., Fire_Disaster/Urban_Fire/*.png)
            category_images.extend(list(category_dir.glob(f"**/*{ext}")))
            
        # Sort to ensure deterministic selection
        category_images.sort()
        
        # Take top 20
        selected = category_images[:20]
        # Store tuple of (image_path, category_name) to preserve top-level folder name
        images_to_process.extend([(img, category_dir.name) for img in selected])
        log.db(f"  Category '{category_dir.name}': found {len(category_images)}, selected {len(selected)}", indent=1)

    if not images_to_process:
        log.warning(f"⚠️ No images found in {IMAGES_DIR}")
        return 0
        
    log.db(f"Seeding total {len(images_to_process)} images to visual_evidence...")
    
    points = []
    failed = 0
    
    for i, (img_path, category) in enumerate(images_to_process):
        try:
            log.embed(f"  [{i+1}/{len(images_to_process)}] Processing: {img_path.name} ({category})", indent=1)
            
            # Load and embed image
            image = Image.open(img_path).convert("RGB")
            inputs = clip_processor(images=image, return_tensors="pt")
            
            with torch.no_grad():
                features = clip_model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            
            embedding = features[0].tolist()
            
            # Use top-level category (Fire_Disaster, not Urban_Fire)
            point = PointStruct(
                id=i,
                vector={"dense": embedding},
                payload={
                    "filename": img_path.name,
                    "category": category,  # Top-level folder name (Fire_Disaster)
                    "subfolder": img_path.parent.name,  # Subfolder name (Urban_Fire)
                    "local_path": str(img_path),
                    "relative_path": str(img_path.relative_to(PROJECT_ROOT.parent)),
                }
            )
            points.append(point)
            
        except Exception as e:
            log.warning(f"  Failed to process {img_path.name}: {e}", indent=2)
            failed += 1
    
    if not points:
        log.warning("⚠️ No images were successfully processed")
        return 0
    
    log.db(f"  Upserting {len(points)} images to Qdrant...", indent=1)
    
    start = time.time()
    client.upsert(collection_name="visual_evidence", points=points)
    elapsed = time.time() - start
    
    log.success(f"✅ Upserted {len(points)} images in {elapsed:.2f}s (failed: {failed})", indent=1)
    
    # Verify
    info = client.get_collection("visual_evidence")
    log.db(f"  Collection now has {info.points_count} points", indent=1)
    
    return len(points)


def main():
    """Main seeding flow."""
    print("\n" + "=" * 60)
    print("  ResQ AI - Qdrant Seeding Script")
    print("=" * 60 + "\n")
    
    # Step 1: Connect to Qdrant
    log.info("Step 1: Connecting to Qdrant Cloud...")
    client = check_qdrant_connection()
    if not client:
        sys.exit(1)
    print()
    
    # Step 2: Clean up existing collections (to avoid Qdrant storage limits)
    log.info("Step 2: Cleaning up existing data...")
    delete_all_collections(client)
    print()
    
    # Step 3: Create collections
    log.info("Step 3: Creating fresh collections...")
    create_collections(client)
    print()
    
    # Step 4: Load embedding models
    log.info("Step 4: Loading embedding models...")
    text_model = load_text_embedding_model()
    if not text_model:
        log.error("Cannot proceed without text embedding model")
        sys.exit(1)
    
    sparse_model = load_sparse_model()
    clip_model, clip_processor = load_clip_model()
    print()
    
    # Step 5: Seed data
    log.info("Step 5: Seeding data to collections...")
    
    total_points = 0
    total_points += seed_incidents(client, text_model, sparse_model)
    print()
    
    total_points += seed_sops(client, text_model)
    print()
    
    total_points += seed_landmarks(client, text_model, sparse_model)
    print()
    
    total_points += seed_images(client, clip_model, clip_processor)
    print()
    
    # Summary
    print("=" * 60)
    log.success(f"🎉 Seeding complete! Total points: {total_points}")
    print("=" * 60)
    
    # Final collection stats
    log.info("\nCollection Statistics:")
    for collection in ["incident_memory", "protocols_sops", "landmark_index", "visual_evidence", "semantic_cache"]:
        try:
            info = client.get_collection(collection)
            log.db(f"  {collection}: {info.points_count} points", indent=1)
        except:
            log.warning(f"  {collection}: empty or not found", indent=1)
    
    print("\n" + "=" * 60)
    log.success("✅ Data is now in Qdrant Cloud permanently!")
    log.info("You do NOT need to re-run this script unless you change clusters.")
    log.info("The 685MB images are no longer needed for SEARCH (only for DISPLAY).")
    print("=" * 60)
    print("\nNext step: docker-compose up --build")


if __name__ == "__main__":
    main()
