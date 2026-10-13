# Radflow Sentinel Pro

Python research utilities for synthetic radiology-system cases, illustrative escalation rules, incidental finding records, and rule-based report screening. The project contains **separate supervisory and clinical Python entry points**, plus a standalone static browser demonstration in `web/`.

> **Research/demo software — not a medical device or validated clinical decision support tool.** The example thresholds are arbitrary, the report parser has limited negation handling, and notification routing does not deliver real messages. Do not use for patient care or enter identifiable patient data.

## What is implemented

- **Supervisory CLI/API** (`cli.py`, `agents/`): three generic threshold/descriptor workers produce a consensus dossier and an in-memory HMAC-SHA256 event chain.
- **Clinical CLI** (`radflow_sentinel_pro/cli.py`): synthetic case evaluation using three separate threshold-based agents; this is the installed `radflow-sentinel-pro` console command.
- **Additional clinical modules**: rule-based radiology report keyword parsing; simplified Fleischner 2017 pulmonary nodule and ACR TI-RADS rule tables; in-memory incidental finding follow-up records; notification attempt logging and HL7 text serialization. These are independent modules, not an integrated PACS/RIS connection.
- **Static browser demo** (`web/`): JavaScript implementations of the supervisory threshold rules, JSON export, and session counters. No backend, cryptographic signing, or patient data upload is involved.

The browser demo is deployable as static assets through GitHub Pages; a Pages workflow is supplied. Its availability depends on repository Pages configuration. The real FastAPI services require a Python host and **do not run on GitHub Pages**.

## Install

Requires Python 3.10–3.12 for the tested CI matrix (package metadata permits Python 3.9+).

```bash
git clone https://github.com/abusuraihsakhri/radflow-sentinel-pro.git
cd radflow-sentinel-pro
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
```

Generate **two different random secrets** for `AUDIT_SECRET_KEY` and `API_TOKEN` (for example, run `python -c "import secrets; print(secrets.token_hex(32))"` twice). Replace the placeholders in `.env`. The supervisory CLI loads `.env` automatically. Do not commit `.env`.

## Commands

```bash
# Supervisory evaluator (uses .env and the HMAC signing key)
python cli.py audit --task-id DEMO-01 --primary 28.5 --secondary 14.2 --critical
python cli.py batch -i sample.csv -o results.csv
python cli.py chat "system status"
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000

# Separate clinical evaluator
radflow-sentinel-pro audit --case-id CASE-01 --primary 26.2 --secondary 12.5 --stat
radflow-sentinel-pro batch -i sample.csv -o clinical-results.csv

# Browser-only local demo
python -m http.server 8080 --directory web
```

Open `http://localhost:8080/` for the demo (not the Python backend).

The sample CSV has `case_id,patient_synthetic_id,metric_primary,metric_secondary,is_stat,status_flag` columns; the supervisory batch interface also accepts `task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor`. Boolean CSV values accept true/false, yes/no and 1/0 (case insensitive). Unknown values fail with a row-numbered error.

## API and security

The supervisory service provides `GET /health`, `GET /metrics` (Prometheus text), `POST /api/audit`, `POST /api/chat` and `GET /api/audit/logs`. The separately installed clinical service provides `GET /health`, `POST /api/audit` and `POST /api/chat`. All endpoints except `/health` require `Authorization: Bearer <API_TOKEN>`. API endpoints return HTTP 503 until a nonplaceholder token is configured. No CORS origins are enabled by default.

The HMAC audit chain is **process-local memory**, not durable storage. Restarting the service deletes it; `verify-audit` checks only records created in the current process. The PHI guard uses limited regex patterns; it is **not validated deidentification, HIPAA certification, or protection against every identifier**. Do not expose these APIs to untrusted networks without production authentication, transport security, persistent storage, and operational review.

```bash
python -m pytest -q
python -m compileall -q agents radflow_sentinel_pro cli.py
node --check web/app.js
```

GitHub Actions runs the Python tests on versions 3.10–3.12 and checks browser JavaScript syntax.

## Container

```bash
docker compose up --build
```

The example Compose port mapping binds to `127.0.0.1:8000`; `.env` supplies runtime credentials. Containers run as a non-root user. Never place secrets in GitHub Pages files.

## Technology and support

Python, FastAPI, Pydantic v2, standard-library rule processing, a vanilla JavaScript/HTML/CSS browser demo, and Docker. The demo requires a modern browser supporting ES2015+ APIs and `Blob` downloads; no browser-Python runtime is included.

## License

MIT — see [LICENSE](LICENSE).
