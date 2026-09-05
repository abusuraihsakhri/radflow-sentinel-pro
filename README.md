# Radflow Sentinel Pro

> **Domain:** Diagnostic Radiology & Medical Imaging AI
> **Reference Guidelines & Standards:** American College of Radiology (ACR) RADS & Fleischner Society

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Radflow Sentinel Pro** is an advanced analytical and computational platform implementing Emergency Critical Finding Escalation & Fleischner 2017 Tracker. It provides:

- **Automated radiology report parsing** with NLP-based critical finding detection
- **Fleischner Society 2017 guideline** compliance for pulmonary nodule management
- **ACR TI-RADS 2017** thyroid nodule risk stratification
- **Critical result notification routing** with ACR-compliant escalation protocols
- **Multi-agent consensus evaluation** with specialized domain workers

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`Severity`** — dedicated module for severity evaluation and state verification.
- **`DomainKnowledgeRegistry`**: Enterprise domain rules, guideline matrices, and evidence benchmarks.
- **`AgentAlert`** — dedicated module for agent alert evaluation and state verification.
- **`AcuteCriticalFinderAgent`**: Primary metric threshold auditor
- **`IncidentalomaTrackerAgent`**: STAT kinetics & closed-loop escalation auditor
- **`ContrastSafetyAuditorAgent`**: Biomarker & concordance triager

### 🏥 Clinical Decision Support

- **`NLPReportParser`**: Rule-based NLP engine for radiology report parsing with clinical entity recognition
- **`FleischnerGuidelines`**: Implements Fleischner Society 2017 guidelines for pulmonary nodule management
- **`TIRADSGuidelines`**: Implements ACR TI-RADS 2017 guidelines for thyroid nodule management
- **`IncidentalomaManager`**: Complete lifecycle management of incidental findings
- **`PACSCriticalResultRouter`**: HL7/DICOM integration for critical result notification routing

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/radflow-sentinel-pro.git
cd radflow-sentinel-pro

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn pydantic pytest

# Configure environment
cp .env.example .env
# Edit .env and set a strong AUDIT_SECRET_KEY
```

---

## 💻 CLI Quickstart & Usage

### 1. Run Single Task Evaluation
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### 2. Query the Supervisory Chat
```bash
python cli.py chat "What is the system status?"
```

### 3. Batch Process CSV Records
```bash
python cli.py batch -i sample.csv -o results.csv
```

### 4. Verify Audit Trail Integrity
```bash
python cli.py verify-audit
```

### 5. Launch FastAPI REST Server
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Parameter Reference
- `--task-id`: Unique task/case identifier
- `--target`: Target entity or specimen identifier
- `--primary`: Primary measurement value (float)
- `--secondary`: Secondary metric value (float)
- `--critical`: Trigger emergency/critical flag
- `--status`: Status/phenotype descriptor

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Unique case identifier | Required |
| `patient_synthetic_id` | Anonymized patient reference | Required |
| `metric_primary` | Primary measurement value | Required |
| `metric_secondary` | Secondary measurement value | Required |
| `is_stat` | STAT/emergency flag | Required |
| `status_flag` | Status descriptor | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition. Full signature verification on integrity checks.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

### Environment Variables

| Variable | Description | Required |
|:---------|:------------|:---------|
| `AUDIT_SECRET_KEY` | HMAC-SHA256 signing key for audit trail | Yes |
| `MODEL_PROVIDER` | LLM provider (mock/ollama/claude/openai) | No (default: mock) |
| `API_HOST` | REST API bind address | No (default: 127.0.0.1) |
| `API_PORT` | REST API port | No (default: 8000) |

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or manually with Docker
docker build -t radflow-sentinel-pro .
docker run -p 8000:8000 --env-file .env radflow-sentinel-pro
```

---

## 📁 Project Structure

```
radflow-sentinel-pro/
├── agents/                  # Enterprise agent framework
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, HMAC audit trail
│   ├── models.py           # Pydantic v2 schemas
│   ├── supervisor.py       # Master orchestrator
│   ├── workers.py          # Specialized domain workers
│   ├── llm_factory.py      # LLM provider factory
│   ├── learning.py         # Bayesian calibration engine
│   ├── metrics.py          # Prometheus metrics exporter
│   └── streamer.py         # WebSocket telemetry broadcaster
├── radflow_sentinel_pro/   # Clinical agent modules
│   ├── agents.py           # Clinical sub-agents
│   ├── engine.py           # Clinical algorithmic engine
│   ├── models.py           # Clinical data models
│   ├── cli.py              # Clinical CLI
│   ├── server.py           # Clinical FastAPI server
│   ├── incidentaloma_manager.py  # Fleischner/TI-RADS management
│   ├── nlp_report_parser.py      # NLP radiology report parser
│   └── pacs_critical_router.py   # PACS critical result routing
├── tests/                  # Automated test suite
├── web/                    # Operations console (HTML/JS)
├── cli.py                  # Main CLI entry point
├── simulator.py            # High-throughput simulation
├── enrichment.py           # Enrichment feature engines
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
└── .env.example            # Environment template
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
