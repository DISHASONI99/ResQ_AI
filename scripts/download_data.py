#!/usr/bin/env python3
"""
Data Setup Script - Synthetic Data Generation

This script:
1. Generates synthetic incident data
2. Generates synthetic SOPs
3. Generates synthetic landmark data

Run once before starting the application.
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import random

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent.parent / "data"
OSM_REGION = "bangalore"

# ============ LOGGING ============
class Logger:
    """Simple colored logger for visibility."""
    
    COLORS = {
        "INFO": "\033[94m",     # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",    # Red
        "RESET": "\033[0m",
    }
    
    @staticmethod
    def log(level: str, message: str):
        color = Logger.COLORS.get(level, "")
        reset = Logger.COLORS["RESET"]
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] [{level}] {message}{reset}")
    
    @staticmethod
    def info(msg): Logger.log("INFO", msg)
    
    @staticmethod
    def success(msg): Logger.log("SUCCESS", msg)
    
    @staticmethod
    def warning(msg): Logger.log("WARNING", msg)
    
    @staticmethod
    def error(msg): Logger.log("ERROR", msg)


log = Logger()





def generate_synthetic_incidents():
    """Generate synthetic incident data for testing."""
    incidents_file = DATA_DIR / "synthetic" / "incidents.json"
    
    if incidents_file.exists():
        log.info("✓ Synthetic incidents already exist. Skipping.")
        return True
    
    log.info("🔧 Generating synthetic incident data...")
    
    incidents_dir = DATA_DIR / "synthetic"
    incidents_dir.mkdir(parents=True, exist_ok=True)
    
    # Bangalore locations
    locations = [
        {"name": "MG Road", "lat": 12.9758, "lon": 77.6045},
        {"name": "Indiranagar", "lat": 12.9784, "lon": 77.6408},
        {"name": "Koramangala", "lat": 12.9352, "lon": 77.6245},
        {"name": "Whitefield", "lat": 12.9698, "lon": 77.7500},
        {"name": "Jayanagar", "lat": 12.9250, "lon": 77.5938},
        {"name": "HSR Layout", "lat": 12.9116, "lon": 77.6389},
        {"name": "Electronic City", "lat": 12.8458, "lon": 77.6692},
        {"name": "Marathahalli", "lat": 12.9591, "lon": 77.6974},
    ]
    
    incident_types = [
        ("Medical_CardiacArrest", "P1", ["ALS_Ambulance"]),
        ("Medical_Trauma", "P2", ["BLS_Ambulance", "Trauma_Kit"]),
        ("Fire_Residential", "P1", ["Fire_Truck", "Water_Tender"]),
        ("Fire_Commercial", "P1", ["Fire_Truck", "Water_Tender", "Ladder_Truck"]),
        ("Accident_Vehicle", "P2", ["Ambulance", "Traffic_Police"]),
        ("Accident_Pedestrian", "P2", ["Ambulance"]),
        ("Rescue_Building_Collapse", "P1", ["NDRF_Team", "Ambulance", "Fire_Truck"]),
        ("HazMat_GasLeak", "P2", ["HazMat_Team", "Fire_Truck"]),
    ]
    
    incidents = []
    for i in range(50):
        loc = random.choice(locations)
        inc_type, priority, assets = random.choice(incident_types)
        
        incident = {
            "id": f"INC-{i+1:04d}",
            "type": inc_type,
            "priority": priority,
            "description": f"Emergency incident at {loc['name']} - {inc_type.replace('_', ' ')}",
            "location": {
                "name": loc["name"],
                "lat": loc["lat"] + random.uniform(-0.01, 0.01),
                "lon": loc["lon"] + random.uniform(-0.01, 0.01),
            },
            "assets_dispatched": [{"type": a, "quantity": 1} for a in assets],
            "status": random.choice(["resolved", "resolved", "resolved", "active"]),
            "timestamp": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00",
            "access_level": random.choice(["dispatcher", "dispatcher", "commander"]),
        }
        incidents.append(incident)
    
    with open(incidents_file, "w") as f:
        json.dump(incidents, f, indent=2)
    
    log.success(f"✅ Generated {len(incidents)} synthetic incidents → {incidents_file}")
    return True


def generate_synthetic_sops():
    """Generate synthetic SOP documents."""
    sops_dir = DATA_DIR / "synthetic" / "sops"
    marker_file = sops_dir / ".generated"
    
    if marker_file.exists():
        log.info("✓ Synthetic SOPs already exist. Skipping.")
        return True
    
    log.info("📝 Generating synthetic SOP documents...")
    
    sops_dir.mkdir(parents=True, exist_ok=True)
    
    sops = [
        {
            "id": "SOP-MED-001",
            "title": "Cardiac Arrest Response Protocol",
            "category": "Medical",
            "access_level": "dispatcher",
            "content": """
# Cardiac Arrest Response Protocol (SOP-MED-001)

## Immediate Actions
1. Confirm unconsciousness - tap shoulders, ask "Are you okay?"
2. Call for backup - Request ALS Ambulance immediately
3. Begin CPR - 30 compressions : 2 breaths ratio
4. Apply AED if available - Follow voice prompts

## Dispatch Requirements
- Primary: ALS Ambulance with Paramedic
- Secondary: BLS Ambulance for transport backup
- ETA Target: < 8 minutes for P1

## Critical Notes
- Do NOT stop CPR until medical team arrives
- If patient is on blood thinners, note for hospital
- Epinephrine 1mg IV every 3-5 minutes if no ROSC
            """,
        },
        {
            "id": "SOP-FIRE-001",
            "title": "Residential Fire Response",
            "category": "Fire",
            "access_level": "dispatcher",
            "content": """
# Residential Fire Response Protocol (SOP-FIRE-001)

## Immediate Actions
1. Confirm fire location and number of floors
2. Evacuate all residents - Account for elderly/disabled
3. Dispatch fire units based on building type

## Dispatch Requirements
- Type A (1-2 floors): 1 Fire Truck + 1 Water Tender
- Type B (3-5 floors): 2 Fire Trucks + 1 Ladder + 2 Water Tenders
- Type C (6+ floors): 3 Fire Trucks + 2 Ladders + 3 Water Tenders + Ambulance

## Critical Notes
- Gas supply must be cut off by GAIL team
- Electricity must be cut off by BESCOM
- Coordinate with traffic police for route clearance
            """,
        },
        {
            "id": "SOP-ACC-001",
            "title": "Vehicle Accident Response",
            "category": "Accident",
            "access_level": "dispatcher",
            "content": """
# Vehicle Accident Response Protocol (SOP-ACC-001)

## Scene Assessment
1. Number of vehicles involved
2. Number of casualties (conscious/unconscious)
3. Fuel/fire hazard present?
4. Traffic obstruction level

## Dispatch Requirements
- Minor (no injuries): Traffic Police only
- Moderate (injuries): Ambulance + Traffic Police
- Severe (multiple casualties): Multiple Ambulances + Fire Truck (for extraction) + Traffic Police

## Critical Notes
- Do NOT move spine injury patients
- Secure scene from oncoming traffic
- Preserve evidence for FIR if fatality
            """,
        },
    ]
    
    for sop in sops:
        filepath = sops_dir / f"{sop['id']}.md"
        with open(filepath, "w") as f:
            f.write(sop["content"])
        log.info(f"   Created: {filepath.name}")
    
    # Save metadata
    metadata_file = sops_dir / "metadata.json"
    metadata = [{k: v for k, v in sop.items() if k != "content"} for sop in sops]
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)
    
    marker_file.touch()
    log.success(f"✅ Generated {len(sops)} SOP documents → {sops_dir}")
    return True


def generate_landmarks():
    """Generate sample Bangalore landmarks (simplified OSM data)."""
    landmarks_file = DATA_DIR / "osm" / "bangalore_landmarks.json"
    
    if landmarks_file.exists():
        log.info("✓ Landmark data already exists. Skipping.")
        return True
    
    log.info("🗺️ Generating Bangalore landmark data...")
    
    osm_dir = DATA_DIR / "osm"
    osm_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample landmarks (would normally come from OSM Overpass API)
    landmarks = [
        {"name": "Sharma General Store", "alt_names": ["Sharma Shop", "Sharmaji Kirana"], "type": "shop", "lat": 12.9758, "lon": 77.6045},
        {"name": "Lakshmi Temple", "alt_names": ["Lakshmi Devi Temple"], "type": "temple", "lat": 12.9345, "lon": 77.6123},
        {"name": "Forum Mall", "alt_names": ["Forum Value Mall"], "type": "mall", "lat": 12.9342, "lon": 77.6101},
        {"name": "Indiranagar Metro Station", "alt_names": ["Indiranagar Metro"], "type": "transit", "lat": 12.9784, "lon": 77.6408},
        {"name": "Sony Signal", "alt_names": ["Sony World Junction"], "type": "junction", "lat": 12.9350, "lon": 77.6120},
        {"name": "Domlur Flyover", "alt_names": ["Domlur Bridge"], "type": "infrastructure", "lat": 12.9610, "lon": 77.6380},
        {"name": "CMH Road", "alt_names": ["Cambridge Layout Main Road"], "type": "road", "lat": 12.9783, "lon": 77.6372},
        {"name": "Koramangala Water Tank", "alt_names": ["Tank Bund"], "type": "landmark", "lat": 12.9350, "lon": 77.6220},
        {"name": "Christ University", "alt_names": ["Christ College"], "type": "education", "lat": 12.9360, "lon": 77.6050},
        {"name": "Manipal Hospital", "alt_names": ["Manipal", "HAL Airport Road Hospital"], "type": "hospital", "lat": 12.9580, "lon": 77.6470},
        {"name": "St. John's Hospital", "alt_names": ["St Johns"], "type": "hospital", "lat": 12.9280, "lon": 77.6210},
        {"name": "Cubbon Park", "alt_names": ["Cubbon"], "type": "park", "lat": 12.9763, "lon": 77.5929},
    ]
    
    with open(landmarks_file, "w") as f:
        json.dump(landmarks, f, indent=2)
    
    log.success(f"✅ Generated {len(landmarks)} landmarks → {landmarks_file}")
    return True


def main():
    """Main download and setup flow."""
    print("\n" + "=" * 60)
    print("  ResQ AI - Data Setup Script")
    print("=" * 60 + "\n")
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    steps = [
        ("Generate Synthetic Incidents", generate_synthetic_incidents),
        ("Generate Synthetic SOPs", generate_synthetic_sops),
        ("Generate Landmark Data", generate_landmarks),
    ]
    
    for step_name, step_func in steps:
        log.info(f"Step: {step_name}")
        try:
            success = step_func()
            if not success:
                log.warning(f"⚠️ {step_name} completed with warnings. Continuing...")
        except Exception as e:
            log.error(f"❌ {step_name} failed: {e}")
            raise
        print()
    
    print("=" * 60)
    log.success("🎉 Data setup complete!")
    print("=" * 60)
    print(f"\nData directory: {DATA_DIR}")
    print("\nNext step: Run the seeding script to push data to Qdrant")
    print("  python scripts/seed_qdrant.py")


if __name__ == "__main__":
    main()
