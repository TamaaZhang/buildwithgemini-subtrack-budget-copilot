# 💳 SubTrack & Budget Copilot

> A personal financial copilot that tracks recurring subscriptions, calculates monthly expenses, simulates savings growth, and generates achievement milestone visuals.

<div align="center">

![SubTrack & Budget Copilot Demo](docs/demo.gif)

</div>

---

## 🎯 What the Agent Actually Does

SubTrack & Budget Copilot is built on the **Google Agent Development Kit (ADK)** and designed to run on **Google Cloud Agent Platform**. It actively manages subscription records, performs financial simulations, and celebrates savings milestones:

1. **Recurring Subscription Tracking & Cataloging**
   - Queries and lists active subscriptions from Cloud Firestore with monthly/annual cost breakdowns.
   - Adds new recurring services or updates existing ones (cost, billing cycle, renewal day, cancellation difficulty).
   - Deletes cancelled subscriptions from the database to reflect instant monthly savings.

2. **Financial Simulations & Currency Conversion**
   - Simulates compound savings interest over customizable timeframes (years, monthly contributions, annual return rate).
   - Converts costs across currencies (USD, TWD, EUR, JPY, GBP, CAD, AUD) using live exchange rates.
   - Executes Python financial logic within a secure Cloud sandbox environment.

3. **Milestone Celebration Media (Visuals & Video)**
   - Generates 3D achievement badges for savings milestones using Vertex AI image generation (`gemini-3.1-flash-lite-image`).
   - Generates animated celebration video clips using Google's Omni model (`gemini-omni-flash-preview`).
   - Saves generated media to the session's Artifacts panel and uploads raw assets directly to a public Cloud Storage bucket, returning public HTTPS URLs.

4. **Agent-to-User Interface (A2UI)**
   - Emits structured A2UI card schemas (`A2uiSchemaManager` v0.8) for clean visual layout rendering across supported frontends.

---

## ☁️ Google Cloud Services & Tools Wired Up

| Capability | Model / Service | Implementation in Code |
|---|---|---|
| **Core Reasoning Agent** | `gemini-3.8-flash` | ADK `Agent` in `app/agent.py` configured with retry options |
| **Cross-Session Memory** | Vertex AI Memory Bank | `PreloadMemoryTool` and `generate_memories_callback` (`add_session_to_memory`) |
| **Structured Database** | Cloud Firestore | `list_subscriptions`, `get_subscription_details`, `add_or_update_subscription`, `delete_subscription` |
| **Asset Storage** | Cloud Storage | Uploads milestone badges (`milestones/`) and videos (`videos/`) returning public HTTPS links |
| **Image Generation** | `gemini-3.1-flash-lite-image` | `generate_milestone_badge` generating custom 3D celebration badges |
| **Video Generation** | `gemini-omni-flash-preview` | `generate_domain_video` generating animated celebration clips via Interactions API |
| **Local Discovery** | Google Places & Geocoding API | `geocode_address` and `find_nearby_places` for finding local service alternatives |
| **Code Sandbox** | Agent Engine Code Sandbox | `AgentEngineSandboxCodeExecutor` for safe execution of financial code |
| **Rich UI Layouts** | A2UI (v0.8) | `BasicCatalog` + `a2ui_callback` interceptor returning structured cards |

---

## 🛠️ Project Structure

```
subtrack-budget-copilot/
├── app/
│   ├── agent.py                 # Core agent definition, prompts, and all tool implementations
│   ├── a2ui_utils.py            # A2UI callback and card formatting utilities
│   ├── fast_api_app.py          # ADK FastAPI backend server
│   └── app_utils/               # A2A protocol and reasoning engine adapters
├── frontend/
│   ├── main.py                  # FastAPI proxy translating browser requests to agent protocol
│   ├── static/index.html        # Modern chat interface with prompt chips and A2UI renderer
│   └── Dockerfile               # Container definition for frontend deployment
├── docs/
│   └── demo.gif                 # Looping demo recording of agent in action
├── agents-cli-manifest.yaml     # Agent deployment manifest configuration
└── pyproject.toml               # Project dependencies and virtual environment configuration
```

---

## 🚀 Local Setup & Run Instructions

### Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Google Cloud SDK (`gcloud`) authenticated with a project having Vertex AI, Firestore, and Cloud Storage enabled.

### 1. Authenticate with Google Cloud
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>
```

### 2. Install Dependencies
```bash
cd subtrack-budget-copilot
uv sync
```

### 3. Launch the ADK Web Playground (Local Agent)
To run the agent locally with hot reloading:
```bash
uv run adk web . --port 8080 --reload_agents
```
Or use the CLI command:
```bash
agents-cli playground
```

### 4. (Optional) Run the Custom Frontend Locally
In a separate terminal, run the FastAPI proxy and chat interface:
```bash
cd subtrack-budget-copilot/frontend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3000
```
Then navigate to port 3000 in your browser to interact with the styled chat UI.
