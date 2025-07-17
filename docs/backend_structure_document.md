#

# Sanad v2 – Technical Stack & Tooling Guide

*Version 1.0  |  Date: 16 Jul 2025*

## 1  Stack Philosophy

Sanad leverages a **modular, cloud‑agnostic stack**: GPU‑accelerated retrieval locally (RTX 4090) and cloud‑hosted LLM APIs. All components are container‑friendly so we can lift‑and‑shift from laptop pilot → AWS VPC → on‑prem.

## 2  Programming Languages & Frameworks

|                                |                                  |                                                         |                                          |
| ------------------------------ | -------------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| Layer                          | Language                         | Framework / Lib                                         | Rationale                                |
| Backend API                    | **Python 3.11**                  | **FastAPI 0.111** / Uvicorn                             | Async I/O, type hints, OpenAPI auto‑docs |
| Agent Logic                    | Python                           | pydantic v2 for typed payloads                          | Safe data handling                       |
| Embeddings & ML                | Python                           | **PyTorch 2.2.1 + CUDA 12.3**, SentenceTransformers 2.5 | GPU support, mature ecosystem            |
| Retrieval Engine               | C++ (native) via Python bindings | **FAISS‑GPU 1.7.4**                                     | Sub‑5 ms similarity search               |
| Front‑end (optional dashboard) | TypeScript                       | React 18, shadcn/ui, Tailwind 3                         | Rapid component dev                      |
| DevOps / IaC                   | YAML/HCL                         | Helm v3, Terraform 1.8                                  | Repeatable infra                         |

## 3  Core Services & Versions

|                     |                                            |               |                       |                                      |
| ------------------- | ------------------------------------------ | ------------- | --------------------- | ------------------------------------ |
| Service             | Technology                                 | Version       | Deployment Mode       | Notes                                |
| **REST Gateway**    | FastAPI + Uvicorn                          | 0.111 / 0.29  | Container             | TLS terminates at Nginx if needed    |
| **Coordinator Svc** | Internal Python module                     | v2.0.0        | Same pod as Gateway   | Houses trigger & enhancer            |
| **Agent Workers**   | Python multiprocessing                     | 2× processes  | Shared GPU            | ThreadPool for LLM calls             |
| **Vector Store**    | FAISS‑GPU                                  | 1.7.4         | In‑memory on 4090     | 24 GB VRAM suffices for 40 k vectors |
| **LLM Providers**   | OpenAI GPT‑4o‑mini; Anthropic Claude Haiku | July 2025 API | Cloud                 | Env‑switchable client                |
| **Observability**   | Prometheus 2.52; Grafana 11                | Helm chart    | Local Docker or cloud | Pushgateway for laptop run           |
| **Logging**         | Loki 2.9 or CloudWatch                     | –             | Stdout scrape         | Trace ID middleware                  |
| **Secrets**         | .env (pilot); AWS SecretsMgr (cloud)       | –             | –                     | Mounted as env vars                  |

## 4  Infrastructure—Laptop Pilot vs AWS

|            |                                   |                                    |
| ---------- | --------------------------------- | ---------------------------------- |
| Component  | Local Pilot (RTX 4090)            | AWS VPC Migration                  |
| Compute    | Ubuntu 22.04 + CUDA 12.3          | EKS 1.30 (g4dn.xlarge node pool)   |
| Storage    | NVMe SSD for `data/`              | S3 bucket `sanad-chunks-prod`      |
| Networking | localhost:8080                    | Private subnets + NAT gateway      |
| Secrets    | `.env` file                       | AWS Secrets Manager (IRSA)         |
| TLS        | None / self‑signed if exposed     | ACM cert on ALB                    |
| CI/CD      | GitHub Actions push → build image | GitHub Actions → ECR → ArgoCD sync |

## 5  Detailed Library Matrix (pip)

`fastapi==0.111.0 uvicorn==0.29.0 python-dotenv==1.0.1 pydantic==2.8.2 sentence-transformers==2.5.1 faiss-gpu==1.7.4.post1 torch==2.2.1+cu123 tqdm==4.66.4 fitz==0.0.1.dev2 # PyMuPDF wrapper openai==1.24.0 anthropic==0.25.3 prometheus-client==0.20.0`

Frozen in `poetry.lock` for reproducibility.

## 6  Containerisation & Orchestration

*   **Dockerfile.multi‑stage** → slim Python base, deps via Poetry, `torch` pinned to CUDA 12 wheel.
*   **docker‑compose.local.yml** for laptop: gateway, prometheus, grafana.
*   **Helm chart** (`charts/sanad/`) for EKS: separate Deployments for gateway, faiss, grafana; HPA on CPU & custom latency metric.

## 7  Data Flow Recap (Pilot)

1.  PDFs chunked to `data/processed/*.json` (≤ 550 tokens).
2.  Embeddings stored in GPU memory FAISS index.
3.  On `/verify`, top‑5 passages pulled, sent to LLM with system prompt.
4.  Agent scoring & optional enhancement, response returned, metrics pushed.

## 8  Security Controls

|                 |                                                                 |             |
| --------------- | --------------------------------------------------------------- | ----------- |
| Layer           | Control                                                         |             |
| Secrets         | `.env` excluded by `.gitignore`; pilot developer responsible.   |             |
| Network         | Only localhost bound; if remote, reverse proxy with basic auth. |             |
| Data at Rest    | PDFs kept on encrypted disk (BitLocker/LUKS) when laptop off.   |             |
| Data in Flight  | HTTPS via self‑signed or mkcert; HSTS disabled for local.       |             |
| Dependency Scan | GitHub Dependabot + `poetry export --without-hashes             | pip-audit`. |

## 9  Performance Benchmarks (RTX 4090)

|                               |            |            |
| ----------------------------- | ---------- | ---------- |
| Stage                         | Mean       | p95        |
| FAISS search (k=5)            | 3 ms       | 6 ms       |
| Draft LLM (150 tok)           | 320 ms     | 380 ms     |
| Agent set (4×60 tok parallel) | 260 ms     | 310 ms     |
| Enhancement (when needed)     | 360 ms     | 420 ms     |
| **E2E**                       | **740 ms** | **980 ms** |

## 10  Future Stack Upgrades (Road‑map)

*   **GraphDB** → Neo4j Aura or ArangoDB for rich provenance.
*   **RL Fine‑Tuning Loop** → AWS SageMaker Pipelines nightly job.
*   **Edge LLM** → Mixtral‑8x7B quantised on RTX 4090 for fully offline mode.
*   **Multi‑cloud** → Pluggable LLM client strategy (`BedrockClient`, `AzureOpenAIClient`).

## 11  Open Issues

|       |                                                                                      |
| ----- | ------------------------------------------------------------------------------------ |
| ID    | Question                                                                             |
| TS‑01 | Keep FAISS index in GPU memory or switch to `nvme` mem‑map when docs > 100 k chunks? |
| TS‑02 | Do we enforce mutual TLS between gateway and FAISS micro‑svc on EKS?                 |
| TS‑03 | Pick Grafana Cloud vs self‑host for SaaS?                                            |

Assign owners before sprint 1.

### Appendix A – Local Dev Commands

`poetry run python scripts/pdf_to_chunks.py data/raw/*.pdf --out data/processed poetry run python scripts/build_indices.py poetry run uvicorn app.main:app --reload --port 8080`
