# PLANNING.md – Canonical Project Charter & Reference

*Sanad v2 Regulatory‑Assurance MVP  |  Version 1.0  |  16 Jul 2025*

**AI Instruction**\
*At the start of every new conversation, load this PLANNING.md and explicitly state:*\
*“I am following the structure and decisions outlined in PLANNING.md (v1.0).”*

## 1  Purpose

Provide a single, top‑level plan that aligns product vision, high‑level architecture, constraints, tech stack, tooling, and success metrics for the Sanad v2 MVP. All other docs (architecture spec, implementation plan, rules, etc.) inherit from this charter.

## 2  Vision & Goals

|         |                                                                      |                                                    |
| ------- | -------------------------------------------------------------------- | -------------------------------------------------- |
| Goal ID | Description                                                          | Target Metric                                      |
| **V‑1** | Deliver **verified** LLM answers with **p95 latency ≤ 1 000 ms**     | Prometheus `http_request_duration_seconds_bucket`  |
| **V‑2** | Improve factual / legal accuracy by **≥ 20 pp** over GPT baseline    | 220‑Q benchmark legal‑hit rate                     |
| **V‑3** | Provide full provenance trace & Sanad‑score in every verified answer | JSON field `sources` & `sanad_score` present 100 % |
| **V‑4** | Pilot on single‑machine RTX 4090, then migrate to AWS single‑tenant  | Laptop success → EKS cluster cut‑over D+90         |

## 3  Scope

*   **In‑scope:** 3 + 1 agents, FAISS retrieval, OpenAI GPT‑4o‑mini (draft/enhance), benchmark harness, dashboards, audit export.
*   **Enhancement: Sophisticated Islamic ʿIlm al-Rijāl Methodology** – Traditional Islamic scholarly evaluation with hierarchical grading, conditional reliability, temporal assessment, and consensus building.
*   **Out‑of‑scope (MVP):** LMIS SQL integration, RL fine‑tune loop, multi‑tenant SaaS, zero‑knowledge proofs.

## 3.1 Islamic Methodology Enhancement (Bolt-On Upgrade)

**Objective:** Transform simple weighted scoring into authentic 1,400-year Islamic scholarly evaluation methodology without breaking existing architecture.

**Strategic Positioning:** Heritage-Led Universal Platform
- **Core Value**: "The only AI platform anchored in 1,400-year-old scholarly methodology and independently audited"
- **Cultural Capital**: Islamic ʿIlm al-Rijāl as competitive moat and premium pricing justification
- **Universal Accessibility**: Triple-label UI (Arabic + Tier + Plain English) for stakeholder comprehension
- **Expansion Strategy**: Domain modules originated from Islamic methodology

**Approach:** Layer sophisticated evaluation on top of current agent framework:
- Current: `sanad_score = 0.4*integrity + 0.3*precision + 0.2*provenance + 0.1*domain`
- Enhanced: `final_score = core_score * certainty_factor` with Islamic grades
- Universal: `domain_module.evaluate(methodology="islamic_hadith")` extensible to any domain

**Core Components:**
- **Traditional Grading System (Tabaqāt):** THIQAH_THABIT, THIQAH, SADUQ, LA_BASH_BIHI, LAYYIN, FIHI_NAZAR, DA_IF, MATRUK, KADHDHAB
- **Conditional Reliability:** Sources reliable from some narrators, unreliable from others
- **Temporal Assessment:** Reliability changes over time (EARLY_CAREER_STRONG, LATER_CAREER_WEAK)
- **Scholarly Consensus (Ijmāʿ):** Multi-agent agreement builds certainty factor
- **Cultural Authenticity:** Scholar attestations with immutable audit trails

**Domain Module Roadmap:**
- **Q4 2025**: Islamic ʿIlm al-Rijāl (flagship methodology)
- **Q1 2026**: Clinical Evidence Module (FDA-adapted from Islamic principles)
- **Q2 2026**: Financial Risk Module (Basel III with Islamic consensus engine)
- **Q3 2026**: Legal Precedent Module (jurisprudence pattern recognition)

**Implementation Strategy:**
- **Non-Breaking:** Existing APIs continue working, add optional grade/certainty fields
- **Modular:** New engines plug into existing IntegrityAgent
- **Fast:** 3 dev-days implementation, minimal latency impact (<1ms)
- **Scalable:** Heritage-led positioning enables premium pricing and market expansion

## 4  High‑Level Architecture

`User → LMIS‑Chat SPA (React) ─┐ │ REST /verify FastAPI Gateway ─► TriggerDetector ─► (no) → Baseline LLM → Response │(yes) ▼ Retriever (FAISS GPU) ▼ ◄─ Parallel Agents (I,P,Prov,Dom) ▼ Coordinator & Enhancer ▼ Verified Response JSON`

*   **Data Stores:** Chunk store (S3 or local `data/processed/`), FAISS index (GPU), Prometheus TSDB.
*   **External APIs:** OpenAI GPT‑4o‑mini; Anthropic Claude Haiku fallback (optional).

## 5  Constraints

|                         |                                         |                                      |
| ----------------------- | --------------------------------------- | ------------------------------------ |
| Category                | Constraint                              | Rationale                            |
| **Latency**             | p95 ≤ 1 000 ms end‑to‑end               | Chat UX & SLA                        |
| **GPU VRAM**            | ≤ 24 GB (RTX 4090)                      | Laptop pilot hardware                |
| **Cost / Verification** | ≤ $0.06                                 | 40 % gross margin at Regulatory tier |
| **Security**            | GDPR, ISO‑27001 controls                | Regulated customers                  |
| **Accuracy**            | ≥ 85 % legal‑hit rate                   | Pilot success gate                   |
| **Open‑source**         | All client‑side deps permissive MIT/BSD | License clarity                      |
| **Data Retention**      | ≤ 180 days default, user erasure < 30 days | GDPR Article 17, privacy by design   |
| **Islamic Authenticity** | Scholarly validation required for methodology changes | Cultural credibility & competitive moat |

## 6  Tech Stack

|                            |                                    |                       |                                  |
| -------------------------- | ---------------------------------- | --------------------- | -------------------------------- |
| Layer                      | Choice                             | Version               | Notes                            |
| **Front‑end**              | React 18, Vite 5, Tailwind CSS 3.4 | TypeScript 5 `strict` | Chat, Dashboard SPA              |
| **Back‑end**               | FastAPI 0.95, Python 3.11          | Poetry for deps       | API + orchestrator               |
| **Agents**                 | OpenAI GPT‑4o‑mini prompts         | openai 1.x SDK        | Integrity, Precision, etc.       |
| **Retrieval**              | FAISS‑GPU 1.7                      | CUDA 12.3             | Chunk size 500 tok + 100 overlap |
| **Embeddings**             | `text-embedding-3-small`           | ‑                     | Pre‑cached offline               |
| **Infrastructure (pilot)** | Docker Compose (GPU flag)          | ‑                     | Single host                      |
| **Infra (cloud)**          | EKS 1.27, Helm 3.10                | Terraform IaC         | Single‑tenant VPC                |
| **Observability**          | Prometheus 2.51, Grafana 10        | Loki logs             | Metrics/export                   |
| **CI/CD**                  | GitHub Actions, ArgoCD             | ‑                     | Lint, test, deploy               |
| **Auth**                   | AWS Cognito (pilot local JWT mock) | OIDC                  | Map roles to claims              |

## 7  Tooling & Work‑flows

*   **Dev Env:** VS Code / Cursor, `.editorconfig`, ESLint + Prettier, Black + isort.
*   **Branching:** `main` (protected) + `feature/*` + `release/*`; squash merge.
*   **CI Stages:** lint → unit tests (Py + TS) → benchmark (85 % gate) → Docker build → image push.
*   **GitOps:** `infrastructure/argocd` with `app-of-apps`; Kustomize overlays per env.

## 8  Quality Gates

|                   |                   |                 |
| ----------------- | ----------------- | --------------- |
| Gate              | Check             | Threshold       |
| **Unit coverage** | Vitest + Pytest   | ≥ 80 % lines    |
| **Benchmark**     | `legal_hit_rate`  | ≥ 85 %          |
| **Latency test**  | Locust 3 QPS load | p95 ≤ 1000 ms   |
| **Lint**          | ESLint / flake8   | no errors       |
| **Docker scan**   | Trivy             | 0 critical CVEs |

## 9  KPIs & Dashboards

*   **Latency:** `http_request_duration_seconds_bucket{route="/verify"}`
*   **Score distribution:** `sanad_score_bucket{le="0.1"...}`
*   **Trigger rate:** `sanad_trigger_total / http_requests_total`
*   **Cost:** tokens × cost per‑tok metric exported via custom gauge.
*   **Cost Monitoring & Alerts:**
    *   **Per-endpoint cost:** `cost_per_verification{endpoint="/verify"}` 
    *   **Monthly budget tracking:** `monthly_token_spend_vs_budget` (alert at 80%)
    *   **Regulatory tier margin:** `gross_margin_percentage` (target >40%)
*   **Islamic Methodology KPIs:**
    *   **Grade distribution:** `islamic_grade_bucket{grade="THIQAH_THABIT"...}`
    *   **Certainty factor:** `certainty_factor_bucket{le="0.8"...}`
    *   **Consensus level:** `agent_consensus_level` (unique grades per evaluation)
    *   **Accuracy improvement:** `accuracy_delta_pp` (percentage points over baseline)
*   **Enterprise Compliance:**
    *   **Backup success rate:** `backup_success_last_7d` (target >99%)
    *   **Security incident count:** `security_incidents_by_severity`
    *   **Data retention compliance:** `data_retention_violations` (target 0)
    *   **License compliance:** `non_permissive_dependencies` (target 0)

Grafana JSON dashboards stored under `infrastructure/grafana/`.

## 10  Risks & Mitigations

|                       |            |                      |                                                        |
| --------------------- | ---------- | -------------------- | ------------------------------------------------------ |
| Risk                  | Likelihood | Impact               | Mitigation                                             |
| LLM API rate‑limits   | Medium     | Latency ↑ / failures | Exponential backoff + two API keys                     |
| FAISS GPU OOM         | Low        | Crash                | Monitor VRAM, shard index                              |
| Accuracy < 85 %       | Medium     | Pilot fail           | Prompt tuning, k‑value ↑                               |
| Single laptop failure | Medium     | Pilot blocked        | Daily index backup; ability to switch to cloud quickly |

## 11  Milestone Schedule (RT = real time days)

|      |                                                      |              |
| ---- | ---------------------------------------------------- | ------------ |
| Day  | Milestone                                            | Owner        |
| D+7  | PDF ingestion + retrieval demo                       | Data Eng     |
| D+28 | Agents + coordinator CLI passes                      | ML Eng       |
| D+42 | FastAPI & React UI integrated                        | Full stack   |
| D+49 | Benchmark ≥ 85 % / p95 ≤ 1 s                        | QA           |
| D+52 | **Islamic Methodology Phase 1 Complete**            | **ML Eng**   |
| D+55 | **Sophisticated Grading & Consensus Engines Live**  | **Backend**  |
| D+60 | Pilot go‑live & LOI secured                          | PM           |
| D+63 | **Islamic UI Enhancement Complete**                  | **Frontend** |
| D+70 | **Full ʿIlm al-Rijāl Methodology Validation**       | **QA Lead**  |
| D+85 | **External Pen Test & Security Compliance Complete** | **Security Lead** |
| D+90 | **Enterprise Production Readiness Certified**       | **Platform Owner** |

### 11.1 Islamic Methodology Milestones Detail

**D+52: Phase 1 Complete**
- Islamic grading constants and enums implemented
- SQLite tables for scholarly profiles
- Basic conditional and temporal engines
- IntegrityAgent outputs traditional grades

**D+55: Sophisticated Engines Live**
- ConditionalReliabilityEngine operational
- TemporalReliabilitySystem functional
- SourceNetworkAnalyzer integrated
- Scholarly consensus calculation active

**D+63: UI Enhancement Complete**
- Arabic grade display (ثقة ثبت, ثقة, صدوق)
- Confidence tooltips with certainty percentages
- Grade-based badge colors
- Conditional assessment indicators

**D+70: Full Methodology Validation**
- Benchmark accuracy improvement ≥ 3-5 percentage points
- Latency impact validation (<1ms overhead)
- Islamic scholarly validation of authenticity
- Competitive moat assessment complete

**D+85: External Pen Test & Security Compliance Complete**
- Third-party penetration testing executed
- STRIDE threat model validation
- SOC-2 Type II control evidence
- Islamic methodology security assessment
- Incident response procedures tested

**D+90: Enterprise Production Readiness Certified**
- Disaster recovery plan validated (RPO <1hr, RTO <2hr)
- GDPR compliance fully implemented
- License scanning integrated in CI/CD
- Cost monitoring and alerting operational
- Regulatory audit preparation complete

**Q1 2026: Domain Module Platform Launch**
- Clinical Evidence Module released (FDA evidence evaluation)
- Islamic methodology white paper published with scholar attestations
- Sanad Methodology Certification Program operational
- First non-Islamic domain customers onboarded

**Q2 2026: Financial Risk Module Release**
- Basel III compliance module using Islamic consensus principles
- "Six Sigma of AI Verification" brand positioning established
- Domain module marketplace infrastructure live
- Billion-dollar platform validation metrics achieved

## 12  AI Assistant Prompting Rules

**Whenever the AI assistant starts a new session or turn, it must:**

1.  Load this PLANNING.md (latest version).
2.  Acknowledge with: *“I am following the structure and decisions outlined in PLANNING.md (v1.0).”*
3.  Apply architectural, tech‑stack, and constraint decisions contained herein.

Failure to reference PLANNING.md invalidates the response per governance rules.

## 13  Change Management

*   Update version header and changelog section when modifying this file.
*   Major revisions require approval from **Platform Owner** and **Org Admin** roles.

*End of PLANNING.md – authoritative project charter.*
