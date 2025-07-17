#

# Sanad™ v2 – Project Requirements Document

## 1  Purpose

Define the detailed product, technical and operational requirements for **Sanad v2 – Regulatory‑Assurance MVP**, to be delivered in a 60‑day sprint and piloted on a single‑machine RTX 4090 setup before migrating to AWS.

## 2  Objectives

1.  Increase factual/legal accuracy of LLM answers by **≥ 20 pp** over baseline.
2.  Deliver verified responses with **p95 latency ≤ 1 000 ms**.
3.  Produce downloadable audit bundles acceptable to EU pharmacovigilance regulators.
4.  Sign at least one paid pilot by Day 60.

## 3  Stakeholders & Roles

|                    |                               |                               |
| ------------------ | ----------------------------- | ----------------------------- |
|                    |                               |                               |
| Role               | Names / Groups                | Interest                      |
| Product Owner      | Founder / PM                  | Scope, roadmap, pilot success |
| Engineering Lead   | ML Eng, Backend, DevOps leads | Architecture, delivery        |
| Compliance Advisor | External Pharma Reg‑expert    | Regulatory alignment          |
| Pilot Users        | Pharmacovigilance Officers    | Day‑to‑day UX                 |
| Investors          | Seed VC                       | KPI attainment                |

## 4  Scope

### 4.1  In Scope

*   Verification engine with **3 + 1 agents** (Integrity, Precision, Provenance, Domain‑LabourLaw).
*   **Trigger detector** (keyword + semantic) invoking Sanad for ≤ 20 % of queries.
*   Retrieval layer using **FAISS‑GPU** and 15‑PDF corpus.
*   REST API (`/baseline`, `/verify`, `/healthz`).
*   Laptop (RTX 4090) deployment scripts; Docker compose.
*   Grafana dashboard (latency, score histograms).
*   Audit PDF generator.
*   Role‑based access (Admin, Verification Mgr, Curator, Standard User, Auditor, DevOps).

### 4.2  Out of Scope (v2)

*   On‑prem graph provenance DB.
*   Reinforcement learning fine‑tune loop (logged only).
*   Third‑party doc connectors (SharePoint, G‑Drive).
*   Full zero‑knowledge privacy engine.

## 5  Functional Requirements

### 5.1  Verification Flow

1.  **Draft** answered by GPT‑4o‑mini.
2.  **TriggerDetector** decides whether to apply Sanad.
3.  **Retriever** returns top‑5 passages.
4.  Agents run in parallel → scores 0‑1.
5.  **Coordinator** computes weighted Sanad_score; if < 0.7, prompts Enhancer to rewrite.
6.  `/verify` returns JSON `{answer, sanad_score, sources[], latency_ms}`.

### 5.2  Core Agents

*   **IntegrityAgent** – validates source authority.
*   **PrecisionAgent** – checks claim‑passage consistency.
*   **ProvenanceAgent** – ensures citation presence.
*   **DomainAgent‑LabourLaw** – regex & LLM rules for Qatar/Labour context.

### 5.3  Retrieval

*   PDFs chunked at 500 tokens, 100 overlap.
*   Embeddings via `all‑MiniLM‑L6‑v2` (384‑dim).
*   Indices: `law.idx`, `nds3.idx`, `research.idx`.

### 5.4  API Contract

*   `POST /baseline` → raw GPT answer.
*   `POST /verify` → SanadResponse (see §7 Data Model).

### 5.5  User Roles & Permissions

*   **Platform Owner** – full tenancy, billing, hard‑delete.
*   **Org Admin** – SSO & corpus upload, config weights.
*   **Verification Manager** – project creation, audit export.
*   **Curator** – document tagging.
*   **Standard User** – run verify, view own history.
*   **Auditor (RO)** – read‑only export access.
*   **DevOps** – infra health, no data view.

### 5.6  Reporting & Dashboards

*   Real‑time latency & score panels.
*   Usage & cost analytics.
*   One‑click audit PDF (unsigned v2; certificate v3).

## 6  Non‑Functional Requirements

|                   |                                                                  |
| ----------------- | ---------------------------------------------------------------- |
|                   |                                                                  |
| Category          | Requirement                                                      |
| **Performance**   | p95 latency ≤ 1 000 ms; throughput ≥ 3 verified QPS on 4090.     |
| **Accuracy**      | Legal‑hit ≥ 85 % on benchmark; Sanad_score mean ≥ 0.75.          |
| **Security**      | API keys in local `.env`; HTTPS if exposed; role R/W separation. |
| **Compliance**    | GDPR retention 30 days; audit log immutable.                     |
| **Scalability**   | Code deployable to EKS without refactor.                         |
| **Observability** | Prometheus metrics, Loki logs.                                   |

## 7  Data Model

`class Passage: doc_id:str; page:int; text:str; dist:float class SanadResponse: answer:str; sanad_score:float; sources:list[Passage]; processing_time_ms:int`

## 8  Integrations

*   **OpenAI GPT‑4o‑mini** – primary LLM.
*   **Anthropic Claude Haiku** – fallback.
*   **Local FAISS‑GPU** – embeddings search.
*   Optional Bedrock client stub.

## 9  Deployment & Hosting (Pilot)

*   OS: Ubuntu 22.04 on laptop with RTX 4090.
*   Python 3.11 via Poetry; Docker optional.
*   All PDFs local; indices cached in RAM/GPU.
*   External calls only to LLM APIs over TLS.

## 10  Branding & UI

*   Palette: Sanad Blue #1F4AFF; Success #27C28B; Error #FF4D4F.
*   Typography: Inter (700 headings / 400 body); JetBrains Mono code.
*   Components: 6 px radius; subtle shadow; 8‑pt grid.
*   Verification badge colours by score band.

## 11  Pricing & Billing (reference for SaaS)

*   Regulatory Tier $2 999/mo incl. 20 k verifs, $0.15 overage.
*   Starter $499, Enterprise $8 999, Government $19 999.

## 12  Success Metrics (KPIs)

|   |                       |            |
| - | --------------------- | ---------- |
|   |                       |            |
| # | KPI                   | Target     |
| 1 | Verification accuracy | ≥ 85 %     |
| 2 | Sanad_score mean      | ≥ 0.75     |
| 3 | p95 latency           | ≤ 1 000 ms |
| 4 | Trigger efficiency    | 10–20 %    |
| 5 | User CSAT             | ≥ 4.2/5    |

## 13  Assumptions

*   LLM APIs remain available and < 500 ms per 150‑token call.
*   15‑PDF corpus fits into 24 GB VRAM index.
*   Pilot users supply benchmark ground‑truth.

## 14  Constraints

*   No internet search allowed (static corpus only).
*   Laptop power/TDP limits sustained QPS.

## 15  Risks & Mitigations

|                         |            |        |                                |
| ----------------------- | ---------- | ------ | ------------------------------ |
|                         |            |        |                                |
| Risk                    | Likelihood | Impact | Mitigation                     |
| LLM rate‑limit          | Med        | High   | Async queue + key pool         |
| Accuracy < 20 pp uplift | Med        | High   | Prompt tuning, k ↑             |
| GPU memory leak         | Low        | Med    | Torch no‑grad, nightly restart |

## 16  Timeline & Milestones

*   **Day 7** – Indices built, retrieval demo.
*   **Day 28** – Agents pass unit tests.
*   **Day 42** – API & Docker on laptop.
*   **Day 49** – Benchmark results (≥ 20 pp uplift).
*   **Day 60** – Pilot deck, first contract.

## 17  Acceptance Criteria

1.  Benchmark CSV shows ≥ 85 % legal-hit and mean score ≥ 0.75.
2.  Grafana dashboard live with latency & score graphs.
3.  Audit PDF export includes answer, passages, checksums.
4.  Pilot user signs off that manual QC time reduced ≥ 50 %.

## 18  Glossary

*   **Sanad_score** – weighted confidence metric 0‑1.
*   **Passage** – fixed‑length text chunk from corpus.
*   **Verification** – process of scoring and (if needed) enhancing an LLM draft.
