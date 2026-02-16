# ResQ AI - Emergency Response Agentic RAG System

> 🚨 **Powered by Qdrant Cloud** - Enterprise-grade vector search with built-in safety, scalability, and security for mission-critical emergency response.

## 🚀 Complete Setup Guide (Fully Reproducible)

Follow these steps exactly to get ResQ AI running on your machine.

---

### **Step 1: Download the Disaster Image Dataset**

The system requires a curated disaster image dataset for visual incident classification.

1. **Download the dataset** from Google Drive:
   ```
   https://drive.google.com/file/d/1bf7PMaWwrJIYvO-js7CgAt4JHJBXNy0u/view?usp=drive_link
   ```

2. **Extract and rename** the folder:
   - After downloading, you'll get a zip file
   - Extract it to get a folder
   - **Rename the folder to exactly**: `Disaster_Dataset`
   - **Move it to**: `ResQ_AI/Disaster_Dataset/`

   Your structure should look like:
   ```
   ResQ_AI/
   ├── Disaster_Dataset/
   │   ├── Damaged_Infrastructure/
   │   ├── Fire_Disaster/
   │   ├── Human_Damage/
   │   ├── Land_Disaster/
   │   ├── Non_Damage/
   │   └── Water_Disaster/
   ├── backend/
   ├── frontend/
   └── ...
   ```

---

### **Step 2: Review Documentation & Presentation**

Before setting up, familiarize yourself with the project:

📂 **Access the documentation folder**:
```
https://drive.google.com/drive/folders/1AX5WtNBxDuB2tKw13T1v-68c8Z4526-Y?usp=drive_link
```

This contains:
- **System Architecture PPT** - High-level overview
- **Technical Documentation** - Detailed implementation guides
- **API Specifications** - Agent contracts and endpoints

---

### **Step 3: Configure API Keys**

ResQ AI requires several API keys for cloud services.

1. **Copy the environment template**:
   ```bash
   cd ResQ_AI
   cp .env.example .env
   ```

2. **Edit `.env` and add your keys**:

   ```bash
   # ============ REQUIRED ============
   
   # Portkey AI Gateway (https://app.portkey.ai)
   PORTKEY_API_KEY="mT3_xxxxxxxxxxxxxxxxxx"
   PORTKEY_CONFIG_ID="pc-resq-a-43e1f8"
   
   # Groq LLM API (https://console.groq.com)
   GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxx"
   
   # Qdrant Vector Database (https://cloud.qdrant.io)
   QDRANT_URL="https://your-cluster-id.region.gcp.cloud.qdrant.io:6333"
   QDRANT_API_KEY="your-qdrant-api-key-here"
   
   # ============ AGENT MODE ============
   AGENT_MODE="prod"  # "prod" for multi-agent, "test" for single model
   
   # ============ LOCAL SERVICES (No changes needed) ============
   REDIS_URL=redis://redis:6379/0
   POSTGRES_URL=postgresql://resq:resq@postgres:5432/resq
   APP_ENV=development
   DEBUG=true
   ```

#### **How to Get Each Key:**

| Service | URL | Steps |
|---------|-----|-------|
| **Portkey** | https://app.portkey.ai | Sign up → Dashboard → API Keys → Copy |
| **Groq** | https://console.groq.com | Sign up → API Keys → Create New Key |
| **Qdrant** | https://cloud.qdrant.io | Create Cluster (GCP) → Cluster Settings → API Keys |

> **Note**: For Qdrant, create a cluster named `resq-ai` on GCP for best compatibility.

---

### **Step 4: Start the System**

Once the dataset and API keys are configured:

```bash
# From the ResQ_AI directory
docker compose up --build
```
**Wait around 20 minutes for the setup to be completely built**

**What happens automatically:**
1. ✅ Backend and frontend containers build
2. ✅ Redis and PostgreSQL databases initialize
3. ✅ Setup container runs `seed_qdrant.py`:
   - Generates synthetic incidents, SOPs, and landmarks
   - Embeds all disaster images using CLIP
   - Uploads everything to Qdrant Cloud
4. ✅ Traefik reverse proxy routes traffic

**Initial setup takes 5-10 minutes** (one-time only). Subsequent starts are instant.

---

### **Step 5: Access the Application**

Once all containers show `✅ Ready`:

**1. Open the landing page:**
```
http://localhost
```

You'll see the **ResQ AI National Emergency Response System** with three role-based portals:

| Portal | Description | Actions |
|--------|-------------|---------|
| **🧑 Public Portal** | Report emergencies as a citizen | `New Incident Form` or `WhatsApp Chat Simulator` |
| **📡 Dispatcher** | Emergency call center console | Review AI-analyzed incidents and dispatch units |
| **🛡️ Commander** | Field operations dashboard | Manage active incidents and update status |

**2. Additional interfaces:**

| Interface | URL | Purpose |
|-----------|-----|---------|
| **API Documentation** | http://localhost/docs | Interactive API explorer (Swagger) |
| **Traefik Dashboard** | http://localhost:8080 | Service health and routing monitor |

---

## 📂 Project Structure

```
ResQ_AI/
├── Disaster_Dataset/           # ⚠️ Downloaded manually (Step 1)
│   ├── Damaged_Infrastructure/
│   ├── Fire_Disaster/
│   ├── Human_Damage/
│   ├── Land_Disaster/
│   ├── Non_Damage/
│   └── Water_Disaster/
│
├── backend/                     # FastAPI Python backend
│   ├── src/
│   │   ├── agents/              # LangGraph multi-agent system
│   │   ├── api/routes/          # REST endpoints
│   │   ├── services/            # Qdrant, LLM, Transcription
│   │   └── main.py
│   └── Dockerfile
│
├── frontend/                    # React + Vite SPA
│   ├── src/
│   │   ├── components/          # Dashboard, Map, Forms
│   │   └── styles/index.css     # Design system
│   └── Dockerfile
│
├── scripts/                     # Data preparation
│   ├── download_data.py         # Synthetic data generator
│   └── seed_qdrant.py           # Vector DB uploader
│
├── config/config.yaml           # App configuration
├── docker-compose.yaml          # Service orchestration
├── .env                         # ⚠️ Created in Step 3
└── README.md                    # This file
```

---

## 🧪 Testing the System

### **Complete End-to-End Workflow**

#### **Step 1: Report an Incident (Public Portal)**

1. Go to http://localhost
2. Click on **"Public Portal"** card
3. Choose either:
   - **"New Incident"** → Fill form with location, description, upload image (optional)
   - **"WhatsApp Chat"** → Type: `"Fire at MG Road, multiple casualties, send ambulances"` and click **Send**

#### **Step 2: AI Processing (Backend)**

The system automatically:
- Extracts location (lat/lon or address)
- Analyzes incident severity using LLM
- Assigns priority (P1/P2/P3/P4)
- Recommends assets (ambulances, fire engines, police)
- Retrieves similar past incidents from Qdrant
- Fetches relevant SOPs (Standard Operating Procedures)

#### **Step 3: Review & Dispatch (Dispatcher Portal)**

1. **Navigate back** to http://localhost
2. Click on **"Dispatcher"** card
3. You'll see the **Dispatcher Console** with:
   - **Pending Queue** (left sidebar) - Incidents awaiting approval
   - **Active Ops** - Currently dispatched incidents
   - **Resolved** - Completed incidents
4. **Click on the new incident** in the Pending queue
5. **Review AI analysis:**
   - Priority level
   - Reasoning and identified risks
   - Recommended assets (ambulances, fire trucks, etc.)
   - Location on map
6. **Adjust priority if needed** (dropdown in bottom panel)
7. Click **"Approve & Dispatch"**
8. Incident moves to **Active Operations**

#### **Step 4: Field Operations (Commander Portal)**

1. **Navigate back** to http://localhost
2. Click on **"Commander"** card
3. You'll see the **Commander Dashboard** with:
   - All active incidents assigned to this commander
   - Asset deployment status (e.g., "En Route (5m)")
   - Public contact information
4. **Update incident status** as the situation evolves:
   - `In Progress` - Arrived on scene
   - `Request Backup` - Need reinforcements
   - `Escalate (P1)` - Situation worsened
   - `Mark Resolved` - Incident closed
5. Changes sync in **real-time** via WebSocket to Dispatcher console

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Vector Database** | **Qdrant Cloud** | Semantic search, image similarity, geo-spatial queries |
| **LLM Gateway** | Portkey AI | Fallback routing (Groq → Cerebras → Google) |
| **Backend** | FastAPI + Python 3.11 | REST API, async processing |
| **Frontend** | React 18 + Vite | Real-time dashboards |
| **Orchestration** | LangGraph | Multi-agent workflow (Supervisor, Triage, Geo, etc.) |
| **Embeddings** | FastEmbed (BGE), CLIP, SPLADE | Text and image vectorization |
| **Audio** | OpenAI Whisper | Speech-to-text for voice reports |
| **Reverse Proxy** | Traefik | Automatic routing and load balancing |

---

## 🎯 Why Qdrant Cloud?

ResQ AI relies on **Qdrant Cloud** for mission-critical vector operations:

### **Key Features Used:**
- **🔒 Built-in Safety**: GDPR-compliant data handling, encryption at rest
- **⚡ Low Latency**: <50ms hybrid search (dense + sparse vectors)
- **📍 Geo-Spatial Filtering**: Find nearest landmarks and resources by coordinates
- **🖼️ Multimodal Search**: Image embeddings (CLIP) for visual incident matching
- **🔄 Horizontal Scaling**: Auto-scales for disaster surge scenarios
- **💾 Persistent Storage**: No data loss during container restarts

### **Collections Used:**
| Collection | Vectors | Purpose |
|------------|---------|---------|
| `incident_memory` | 768D (BGE) + SPLADE | Historical incidents for context retrieval |
| `sop_knowledge` | 768D (BGE) | Standard Operating Procedures |
| `landmark_db` | 768D (BGE) | Geo-tagged landmarks for location resolution |
| `disaster_images` | 512D (CLIP) | Visual similarity search |

**Thank you to Qdrant for providing the robust, production-ready vector database that powers ResQ AI's intelligent triage system.**

---

## 🔑 API Endpoints

### **Incident Management**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/incidents/` | Create incident (text only) |
| POST | `/api/incidents/multimodal` | Create incident (audio/image/location) |
| POST | `/api/incidents/{id}/approve` | Human-in-the-loop approval |
| GET | `/api/incidents/{id}` | Retrieve incident details |

### **Search & Retrieval**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/search/` | Hybrid text search (dense + sparse) |
| POST | `/api/search/visual` | Image similarity search (CLIP) |
| POST | `/api/search/landmarks` | Geo-spatial landmark search |

### **Health & Monitoring**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/ready` | Readiness probe (Qdrant + LLM connectivity) |

**Interactive API Docs**: http://localhost/docs

---

## 🎓 For Developers

### **Agent Architecture**

ResQ AI uses a **LangGraph-based multi-agent system**. See `docs/enhanced_agent_contract.md` for:
- Agent interface specifications
- State machine definitions
- Message schemas

**Agents:**
1. `SupervisorAgent` - Routes intent to specialized agents
2. `TriageAgent` - Assigns priority (High/Medium/Low)
3. `GeoAgent` - Resolves location from text/coordinates
4. `ProtocolAgent` - Retrieves SOPs from Qdrant
5. `VisionAgent` - Analyzes incident images
6. `ReflectorAgent` - Self-critique and validation (optional)

### **Data Flow**

```
WhatsApp/Form Input
    ↓
FastAPI Backend (/api/incidents/multimodal)
    ↓
LangGraph Orchestration
    ↓
[Supervisor] → [Triage, Geo, Vision] → [Protocol]
    ↓
Qdrant Hybrid Search (BGE + SPLADE + CLIP)
    ↓
LLM Synthesis (Portkey → Groq/Cerebras)
    ↓
Response → Dispatcher Dashboard
```

### **Local Development**

```bash
# Backend only (with hot reload)
cd backend
pip install -e ".[dev]"
uvicorn src.main:app --reload

# Frontend only (with HMR)
cd frontend
npm install
npm run dev

# Run Qdrant locally (optional, instead of cloud)
docker run -p 6333:6333 qdrant/qdrant
```

---

## 📋 Environment Variables Reference

**Required:**
```bash
PORTKEY_API_KEY       # Portkey AI Gateway key
PORTKEY_CONFIG_ID     # Fallback routing config ID
GROQ_API_KEY          # Groq LLM API key
QDRANT_URL            # Qdrant cluster URL
QDRANT_API_KEY        # Qdrant authentication key
```

**Optional (Advanced):**
```bash
PORTKEY_CONFIG_FAST   # 8B models (Supervisor, Geo, Vision)
PORTKEY_CONFIG_MEDIUM # 32B models (Triage)
PORTKEY_CONFIG_HEAVY  # 70B models (Reflector)
CEREBRAS_API_KEY      # For Cerebras fallback
GOOGLE_API_KEY        # For Gemini fallback
```

**Defaults (No changes required):**
```bash
REDIS_URL=redis://redis:6379/0
POSTGRES_URL=postgresql://resq:resq@postgres:5432/resq
AGENT_MODE=prod
APP_ENV=development
DEBUG=true
```

---

## 🐛 Troubleshooting

### **"Cannot connect to Qdrant"**
- Verify `QDRANT_URL` ends with `:6333`
- Check API key is correct in `.env`
- Ensure cluster is running in Qdrant Dashboard

### **"Portkey rate limit exceeded"**
- Free tier has 100 requests/day
- Add `GROQ_API_KEY` for direct fallback
- Or upgrade Portkey plan

### **"Disaster_Dataset not found"**
- Ensure folder is named exactly `Disaster_Dataset`
- Check it's in `ResQ_AI/Disaster_Dataset/`
- Re-run `docker-compose down && docker-compose up --build`

### **"Setup container keeps restarting"**
- Check logs: `docker-compose logs setup`
- Verify all API keys are valid
- Ensure Qdrant cluster is reachable

---

## 📜 License

This project is built for educational and emergency response purposes. See `LICENSE` for details.

---

## 🙏 Acknowledgments

- **Qdrant** - For providing the robust, secure, and scalable vector database that powers our intelligent triage system
- **Portkey AI** - For unified LLM gateway with automatic fallback
- **Groq** - For ultra-fast inference
- **FastAPI** - For the incredible async framework
- **React Team** - For the modern UI library

---

**Built with ❤️ for safer communities**
