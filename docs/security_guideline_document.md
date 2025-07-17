#

# Sanad v2 – Back‑End Structure & API Blueprint

*Version 1.0  |  Date: 16 Jul 2025*

## 1  Purpose

Define the folder layout, service boundaries, API contracts, data stores, and operational tooling for the **Sanad v2 Regulatory‑Assurance MVP**. This is the single source of truth for all back‑end engineers, DevOps, and security reviewers.

## 2  High‑Level Architecture Recap

`FastAPI Gateway ─► Coordinator Service ─► (a) TriggerDetector ├─► (b) Retriever (FAISS GPU) ├─► (c) Agent Pool (Integrity / Precision / Provenance / Domain) ├─► (d) Enhancer └─► ResponseBuilder ─► Client`

*All components run as separate ****Python micro‑services in one pod**** for the laptop pilot; will split to multiple pods in AWS.*

## 3  Repository & Folder Layout

`sanad_mvp/ ├─ app/ # FastAPI entrypoints │ ├─ main.py # Uvicorn bootstrap │ ├─ api_router.py # Versioned routes │ └─ deps.py # Auth, DB session providers │ ├─ core/ # Domain‑agnostic engine │ ├─ config.py # Pydantic Settings class │ ├─ logging.py # Structured JSON logger (loguru) │ ├─ metrics.py # Prometheus client, histograms │ └─ types.py # TypedDict / Pydantic models │ ├─ trigger/ │ └─ detector.py # keyword + embedding router │ ├─ retrieval/ │ ├─ embedder.py # SentenceTransformers wrapper │ ├─ retriever.py # FAISS GPU calls │ └─ chunk_store.py # Lazy‑load JSON chunks from disk/S3 │ ├─ agents/ │ ├─ base.py # AbstractAgent class │ ├─ integrity.py # LLM call │ ├─ precision.py # LLM call │ ├─ provenance.py # Rule + LLM mix │ └─ domain_labour.py # Regex + LLM for labour law │ ├─ coordinator/ │ ├─ orchestrator.py # Fan‑out, weight matrix, threshold │ └─ enhancer.py # Regenerates answer if needed │ ├─ db/ │ ├─ models.py # SQLAlchemy (SQLite for pilot) │ └─ crud.py # Feedback, audit logs │ ├─ scripts/ # CLI tools (chunk, build_index...) ├─ tests/ # pytest + unit & integration suites ├─ Dockerfile └─ pyproject.toml`

## 4  Micro‑Service Responsibilities

|                 |                               |                     |                                                                                                 |
| --------------- | ----------------------------- | ------------------- | ----------------------------------------------------------------------------------------------- |
| Service         | Path                          | Runtime             | Key Ops                                                                                         |
| **gateway**     | `app/main.py`                 | FastAPI + Uvicorn   | Auth, rate‑limit, CORS, routing to `/baseline`, `/verify`, `/metrics`, `/healthz`               |
| **coordinator** | `coordinator/orchestrator.py` | Python threadpool   | Receives draft answer & passages, orchestrates agent futures, computes score, triggers enhancer |
| **retriever**   | `retrieval/retriever.py`      | PyTorch CUDA        | Host FAISS index in‑memory on GPU; cosine search                                                |
| **agent‑pool**  | `agents/*`                    | OpenAI SDK calls    | Docker env var `LLM_PROVIDER` toggles between GPT & Claude                                      |
| **db‑logger**   | `db/`                         | SQLAlchemy (SQLite) | Stores query, score, processing time, feedback                                                  |

*(All share process in pilot; will scale vertically on RTX 4090.)*

## 5  API Contracts

### 5.1 Public REST

`POST /baseline req: { question: string } res: { answer: string, latency_ms: int } POST /verify req: { question: string } res: { answer: string, sanad_score: float, sources: [ { doc_id:string, page:int, text:string } ], processing_ms: int }`

*HTTP 422 on validation error, 429 on rate‑limit, 500 on internal.*

### 5.2 Internal gRPC (planned AWS split)

*   `RetrievePassages(SearchRequest) returns SearchResponse`
*   `ScoreDraft(AgentRequest) returns AgentScore`

## 6  Core Data Models (Pydantic)

`class SourcePassage(BaseModel): doc_id: str page: int text: str distance: float class VerificationRequest(BaseModel): question: str class VerificationResponse(BaseModel): answer: str sanad_score: condecimal(gt=0, lt=1) sources: list[SourcePassage] processing_ms: int`

## 7  Configuration & Secrets

*   `SANAD_CONFIG_PATH` — YAML; loaded via `core.config.Config` (singleton)
*   `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — env vars (dotenv for dev)
*   `WEIGHT_MATRIX_JSON` — override default weights at runtime

## 8  Observability

|                   |                                        |                    |
| ----------------- | -------------------------------------- | ------------------ |
| Metric            | Prometheus Key                         | Source             |
| Request latency   | `sanad_request_latency_ms` (histogram) | gateway middleware |
| Sanad score       | `sanad_score` (histogram)              | coordinator        |
| FAISS search time | `faiss_search_ms`                      | retriever          |
| LLM token count   | `llm_tokens_total`                     | agents             |

Structured logs ➜ Loki; trace ID attached per request.

## 9  Security Controls

*   **JWT Auth** via FastAPI dependency; HS256 secret for pilot, OIDC planned.
*   **Rate‑limit** 5 req/s (sliding window) using `slowapi`.
*   **CORS** allow‑list `localhost:5173` only.
*   **Secrets** kept in `.env`; DO NOT commit.
*   **Dep Injection** (FastAPI) ensures testability & limited surface.

## 10  Testing Strategy

|             |                                  |                                      |
| ----------- | -------------------------------- | ------------------------------------ |
| Level       | Tool                             | Coverage                             |
| Unit        | pytest, pytest‑mock              | agents, retriever, detector (≥ 90 %) |
| Integration | httpx + TestClient               | `/verify` flow with mocked LLM       |
| Performance | Locust                           | Sustained 3 QPS, p95 < 1 s           |
| GPU CI      | GitHub self‑hosted runner (4090) | FAISS smoke │                        |

## 11  Deployment & Ops (Laptop Pilot)

1.  `python -m venv .venv && pip install -r requirements.txt`
2.  Run `scripts/pdf_to_chunks.py` then `scripts/build_indices.py`.
3.  `uvicorn app.main:app --workers 2 --port 8080`.
4.  Export Prometheus metrics at `http://localhost:8080/metrics`.

For AWS VPC: Helm chart with two deployments (API & retriever‑GPU), ALB ingress, EBS for SQLite → Aurora later.

## 12  Open TODOs

|       |                                                   |          |
| ----- | ------------------------------------------------- | -------- |
| ID    | Description                                       | Priority |
| BE‑01 | Swap SQLite → Postgres when moving to AWS         | P1       |
| BE‑02 | Implement `error_agent` for graceful LLM failures | P2       |
| BE‑03 | Write gRPC stubs for future micro‑split           | P2       |
| BE‑04 | Add `/feedback` endpoint storing thumbs signal    | P1       |
| BE‑05 | Terraform module for GPU nodegroup                | P1       |

**End of document** – maintain by Back‑End Lead; update on every major refactor or new micro‑service addition.
