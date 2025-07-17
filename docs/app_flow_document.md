#

# Sanad v2 – Application Flow Document

*Version 1.0  |  Date: 16 Jul 2025*

## 1  Purpose

Provide a step‑by‑step, implementation‑ready description of every runtime flow in **Sanad v2 Regulatory‑Assurance MVP** — from user input to verified response, including error and admin paths. This supplements the architecture spec and requirements doc.

## 2  Glossary

|                     |                                                                   |
| ------------------- | ----------------------------------------------------------------- |
| Term                | Definition                                                        |
| *Verification Call* | HTTP POST `/verify` returning `SanadResponse` JSON                |
| *Baseline Call*     | HTTP POST `/baseline` returning raw LLM answer                    |
| *Sanad Score*       | Weighted composite of Integrity, Precision, Provenance, Domain    |
| *Passages*          | Top‑k text chunks retrieved from FAISS                            |
| *Enhancer Pass*     | Second LLM call to rewrite answer when score < threshold (0.70)   |
| *Trigger*           | Boolean result of `TriggerDetector` deciding whether to run Sanad |

## 3  Happy‑Path Flow (Verified Response)

### 3.1 Sequence Steps

1.  **User Question** → arrives via LMIS UI; frontend sends `POST /verify` with `trace_id` header.
2.  **FastAPI Gateway** logs receipt time → forwards body to `FlowController`.
3.  **Trigger Detection** (`TriggerDetector.use_sanad(q)`):    * Keyword scan (O(1))    * Embedding similarity > 0.72    → returns **True** (continue) or **False** (skip to Step 6).
4.  **Draft Generation** (`BaselineLLM.draft()`):    * 150 tokens max reply from GPT‑4o‑mini; streamed.
5.  **Retrieval Route** (`Retriever.route()`):    * Chooses FAISS index (`law` / `nds3` / `research`) → gets top‑5 `Passage[]` in < 5 ms on GPU.
6.  **Parallel Agent Fan‑out** (Integrity, Precision, Provenance, Domain):    * Each receives {question, draft, passages}    * Each returns `score float` + `notes str` (LLM 60 tokens)    * ThreadPoolExecutor with 4 workers; timeout = 850 ms.
7.  **Composite Score** `S = Σ(score_i × weight_i)`    * If `S ≥ 0.70` → **skip** Enhancer → go to Step 9.    * Else → proceed to Step 8.
8.  **Enhancer Pass** (`Enhancer.rewrite()`):    * Prompt = "Using only passages A‑E, produce concise answer…" (≤ 250 tokens)    * New answer replaces draft; agents’ notes appended.
9.  **Response Builder** assembles:

`{ "answer": "…", "sanad_score": 0.83, "sources": [ {"doc_id":"labour_law","chunk_id":21,"page":14}, … ], "processing_time_ms": 812 }`

1.  **Prometheus & Loki log** counters increment (latency, tokens, score).
2.  **Gateway → UI**; frontend shows green badge if score ≥ 0.85.

### 3.2 Latency Budget (ms)

|                        |           |             |
| ---------------------- | --------- | ----------- |
| Component              | P50       | P95         |
| Draft LLM              | 300       | 350         |
| Retrieval              | 5         | 8           |
| Agents (×4)            | 220       | 280         |
| Enhancer (conditional) | 0 / 350   | 0 / 400     |
| Glue + serialization   | 20        | 30          |
| **Total**              | 545 / 895 | 668 / 1 068 |

## 4  Baseline Flow (No Verification)

1.  Trigger returns **False**.
2.  FastAPI calls `BaselineLLM.draft()` (150 tok).
3.  Returns JSON `{answer, sanad_score:0.0, sources:[]}`.
4.  Latency target ≤ 450 ms.

## 5  Error & Degradation Paths

|         |                              |                                                             |                                                  |
| ------- | ---------------------------- | ----------------------------------------------------------- | ------------------------------------------------ |
| Code    | Condition                    | Handling                                                    | User Impact                                      |
| **503** | LLM provider timeout (> 3 s) | Retry once; if fails, return 503 with msg "LLM unavailable" | User sees toast, encouraged to retry             |
| **429** | Token rate limit exceeded    | Queue up to 10 s or fall back to Claude Haiku               | Slight delay; logged to Prometheus               |
| **507** | GPU OOM during FAISS encode  | Switch to CPU index; warn DevOps                            | +25 ms latency burst                             |
| **5xx** | Agent fails                  | Exclude that score; degrade weights proportionally          | Score field shows `agent_error:true`; badge grey |

## 6  Admin Flow – Adding New Corpus

1.  Org Admin uploads PDF via web or CLI.
2.  `IngestionService`:    * Extract text (PyMuPDF) → chunks JSON.    * Store `data/processed` local (pilot) or S3 (cloud).    * Call `IndexService.append()` to add embeddings; emits `ingest_complete` event.
3.  Dashboard increments “Docs Ingested” count; ready for queries.

## 7  Audit Export Flow

1.  Verification Manager clicks "Export Month‑end Audit".
2.  Backend gathers:    * All `/verify` logs between dates.    * SHA‑256 checksums of cited passages.
3.  Jinja2 populates `audit_template.tex`; PDF built via `xelatex`.
4.  Signs PDF with org RSA key; stores in `audit/exports/`.
5.  Download link emailed; entry logged for tamper trail.

## 8  Feedback & RL Loop

1.  User thumbs‑down answer.
2.  Frontend POST `/feedback` {q_id, sentiment:'down', comment}.
3.  `FeedbackCollector` writes to SQLite; nightly cron packages CSV to S3.
4.  RL pipeline (future) samples data → fine‑tunes policies.

## 9  Local Pilot Specifics (RTX 4090)

|               |                                                                            |      |
| ------------- | -------------------------------------------------------------------------- | ---- |
| Service       | Deployment                                                                 | Note |
| FAISS GPU     | Docker compose service `faiss` uses `--gpus all`; mounts processed chunks. |      |
| FastAPI       | Host network on :8080; env `CUDA_VISIBLE_DEVICES=0`.                       |      |
| Grafana       | Node exporter + Prometheus on :3000 for local metrics.                     |      |
| Chunk caching | Keep JSON in RAM (≈1 GB).                                                  |      |

## 10  Future Flow Extensions

*   **Multi-index query planner** (if question spans law + research).
*   **Graph provenance query** to visualise chain of references.
*   **Offline first** mode: on‑prem LLM weight loaded from GGUF.

*Document owner: Engineering Lead.*

*Next review: Sprint 1 Day 3.*
