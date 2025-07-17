 Overview

The diagram below shows the complete runtime flow—from a user question in the LMIS chat UI to a verified Sanad response, including error and admin branches.  It is written in Mermaid v10 syntax so designers can copy‑paste into Figma, Obsidian, or Docs and get an auto‑rendered SVG.

flowchart TD
    subgraph User & Front‑End
        A[User types question]<br>Chat UI
    end

    subgraph Gateway (FastAPI)
        B[POST /ask]
    end

    A -->|HTTP| B
    B --> C{Trigger Detector?<br/>use_sanad(question)}

    %% Baseline path
    C -- No --> D[Call Baseline LLM]<br/>/baseline
    D --> E[Return draft answer]
    E --> F[Gateway responds]

    %% Sanad path
    C -- Yes --> G[Retriever.route()<br/>FAISS GPU search]
    G --> H[Baseline LLM draft]
    H --> I[Parallel Agents<br/>Integrity / Precision / Provenance / Domain]
    I --> J[Coordinator<br/>weighted Sanad_score]
    J --> K{Score ≥ 0.70?}
    K -- Yes --> L[Use draft as final]
    K -- No  --> M[Enhancer prompt<br/>rewrite with passages]
    M --> N[Improved answer]
    L & N --> O[Gateway responds<br/>JSON {answer,score,sources}]

    %% Logging & Monitoring
    subgraph Observability
        P[Prometheus metrics]<br/>latency,score
        Q[CloudWatch /Loki Logs]
        R[Dashboard / Grafana]
    end
    O --> P
    O --> Q
    P --> R
    Q --> R

    %% Error handling
    D -- Error --> E1[HTTP 5xx]
    G -- no passages --> E2[Fallback to draft<br/>score 0.30]
    anyError --> S[Return graceful 500 + traceID]

    %% Admin flows
    subgraph Admin
        T[Upload PDF corpus]
        U[Chunker + Embedder]
        V[FAISS Index Builder]
        W[Update config.yaml]
    end
    T --> U --> V --> G
    W --> B


---

## 2  Colour / Style Suggestions (optional)
If you paste this Mermaid into Figma / Docs, apply these class styles for brand consistency:

```mermaid
classDef primary fill:#1F4AFF,color:#fff,stroke:#172FCC;
classDef decision fill:#FFB020,color:#111,stroke:#C98200;
classDef success fill:#27C28B,color:#fff,stroke:#1B8E65;
class A,B,D,E,F,G,H,I,J,L,N,O primary;
class C,K decision;
class R success;

3  How to Use