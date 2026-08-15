# SautiCivic Bridge

**Sahara CodeSwitch Africa Challenge — Legal & Public Services Track**

A voice-first civic reporting pipeline that transcribes code-switched citizen complaints (Nigerian Pidgin / Yoruba / English), classifies them as infrastructure issues or legal grievances, and generates the correct downstream artifact — a municipal ticket or a Legal Aid Intake Brief. A confidence/completeness gate abstains and asks a clarifying question rather than guessing when the system isn't sure enough to act safely.

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for Postgres)
- Node.js 20+ (for frontend, optional)

### 1. Clone & set up environment
```bash
git clone <repo-url> && cd sauticivic-bridge
cp .env.example .env
# Edit .env with your API keys if using real ASR (optional for mock pipeline)
```

### 2. Start the database
```bash
cd infra && docker-compose up -d db
```

### 3. Install Python dependencies & run the backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000`. Try:
```bash
curl -X POST http://localhost:8000/intake \
  -H "Content-Type: application/json" \
  -d '{"text": "There is a big pothole for Allen Avenue junction, e don spoil plenty tyre."}'
```

### 4. Run tests
```bash
cd backend
python -m pytest
```

### 5. Run the gate demo (no server needed)
```bash
cd backend
PYTHONPATH=. python demo_gate.py
```

## Project Structure
See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system flow, module ownership, and design rules.
See [SOLUTION_DESCRIPTION.md](docs/SOLUTION_DESCRIPTION.md) for the problem statement and key technical decisions.
See [IMPLEMENTATION_PLAN.md](SAUTICIVIC_IMPLEMENTATION_PLAN.md) for the 5-week build timeline.

## Key Design Decisions
1. **Abstention is a first-class outcome** — the confidence/completeness gate prevents wrong artifacts from being silently generated.
2. **Downstream accuracy, not WER alone** — we measure whether transcription errors actually corrupt the generated artifact.
3. **Oracle-vs-ASR attribution** — every benchmark failure is attributed to the correct layer (ASR vs. reasoning).
4. **Text fallback from day one** — voice and text inputs share the identical pipeline.

## License
TBD
