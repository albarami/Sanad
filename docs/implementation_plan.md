# .windsurfrules – Canonical Repository Manifest

*Sanad v2 Regulatory‑Assurance MVP  |  Created 16 Jul 2025*

## 1  Project Overview  

|                     |                                                                                                                                                                 |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Key                 | Value                                                                                                                                                           |
| **Type**            | `windsurf_file`                                                                                                                                                 |
| **Description**     | *Sanad™ Universal AI Verification Platform – 3 + 1‑Agent Architecture Powered by Islamic Epistemological Methodology; Global, Regulated‑industry grade.*        |
| **Primary Goal**    | *Deliver verified AI responses with p95 latency ≤ 1 000 ms & legal‑hit accuracy ≥ 85 % for EU pharmacovigilance pilot on single‑host RTX 4090 → later AWS VPC.* |
| **Current Version** | `v2.0.0‑alpha`                                                                                                                                                  |
| **Repo Root**       | <https://github.com/albarami/Sanad>                                                                                                                             |
| **Compliance Maps** | ISO‑27001 A.14, SOC‑2 CC5, NIST RMF step 3                                                                                                                      |

## 2  Project Structure  

### 2.1 Framework‑Specific Routing  

|                               |                                                                                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stack                         | Rule                                                                                                                                                                                    |
| **React 18 – React Router 6** | All page modules reside in `src/routes/` and are registered via `createBrowserRouter()`.Each route file exports default element **and** route‑level `loader` (TanStack Query prefetch). |
| **FastAPI 0.95**              | API modules live under `backend/api/`.`APIRouter` prefix mirrors file name (e.g., `verify.py` → `/verify`). Middleware to tag `X‑Trace‑ID` header for every response.                   |
| **Prometheus**                | Metrics endpoints `/metrics` secured via basic‑auth; path exempt from JWT auth middleware.                                                                                              |
| **Grafana Dashboards**        | JSON model stored in `ops/grafana/dashboards/` – must be imported during Terraform apply.                                                                                               |

### 2.2 Core Directories  

`repo/ ├─ src/ # React front‑end │ ├─ components/ui # shadcn-derived primitives │ ├─ pages # top‑level routes │ ├─ layouts # AppShell, AuthShell │ ├─ hooks # custom hooks (useSanadScore) │ └─ styles # global.css, tailwind.config.ts ├─ backend/ │ ├─ app # FastAPI factory, settings │ ├─ api # REST routers │ ├─ services # Flow orchestration & agents │ ├─ retriever # FAISS GPU wrapper │ ├─ models # Pydantic v2 schemas │ └─ tests # Pytest + coverage ├─ data/ │ ├─ raw # Uploaded PDFs │ ├─ processed # Chunk JSONs (git‑ignored) │ └─ index # FAISS .idx files (git‑ignored) ├─ config/ # YAML configs (weights, triggers) ├─ ops/ │ ├─ helm/ # Charts for front & back │ ├─ terraform/ # AWS VPC, EKS, RDS, S3 │ └─ scripts # CI helper bash / PowerShell └─ docs/ # MD specs, Mermaid diagrams`

### 2.3 Key Files  

|                                       |                                                       |
| ------------------------------------- | ----------------------------------------------------- |
| Path                                  | Purpose                                               |
| `src/index.tsx`                       | React root, RTK Query provider, i18n init             |
| `src/pages/Verify.tsx`                | Chat panel with `/verify` POST + sources drawer       |
| `backend/main.py`                     | Uvicorn entry; mounts routers, Prom metrics           |
| `backend/services/flow_controller.py` | Implements end‑to‑end Sanad flow                      |
| `config/weights.yaml`                 | Integrity 0.4 / Precision 0.3 / Prov 0.2 / Domain 0.1 |
| `.github/workflows/ci.yml`            | Lint → Unit → E2E → Docker build + push               |

## 3  Tech‑Stack Rules  

### 3.1 Version Enforcement  

*   **react@18.3.x** – functional components only; enable Concurrent features flag off until v2.1.
*   **typescript@5.x** – `strict`, `exactOptionalPropertyTypes` true; no `any`.
*   **tailwindcss@3.4.x** – custom theme token file `tailwind.preset.ts`.
*   **fastapi@0.95.x** & **pydantic@2.x** – use `Annotated` DI pattern.
*   **faiss‑gpu@1.7.4** – IVF‑Flat, 384‑d vectors; recall ≥ 0.9 top‑5.
*   **openai‑python@1.x** – `gpt‑4o-mini`; streaming disabled for verification.
*   **anthropic‑python@0.21.x** – fallback; latency must be < 400 ms / 150 tok.
*   **docker@20+** – multi‑stage; final image `alpine‑slim`, non‑root UID 1001.
*   **kubernetes@1.27** – PodSecurity level `restricted`; NetworkPolicy allow egress 443 only.
*   **helm@3.10+** – Charts versioned `0.1.X` for dev, `1.0.0` for production.

### 3.2 Coding Conventions  

*   Prettier & ESLint share Airbnb config; run `npm run lint:fix` on pre‑commit.
*   Python: black 23.11, isort, flake8; `pyproject.toml` central config.
*   Commit messages – Conventional Commits (`feat:`, `fix:`, `docs:` …).
*   Branch naming: `feat/<ticket>‑<slug>`.

### 3.3 Build / Deploy Rules  

|                    |                 |                |
| ------------------ | --------------- | -------------- |
| Stage              | Tool            | Must Pass      |
| **Lint**           | ESLint / black  | 0 errors       |
| **Unit**           | Vitest / Pytest | cov ≥ 80 %     |
| **Visual**         | Chromatic       | diff ≤ 1 px    |
| **Docker**         | Buildx          | image < 450 MB |
| **Helm Lint**      | `helm lint`     | success        |
| **Terraform Plan** | tf 1.8          | no drift       |

## 4  PRD Compliance 

*   **Latency p95 ≤ 1 000 ms** – enforced by Prometheus alert `sanad_latency_p95_gt_1000ms` (5 m).
*   **Sanad_score mean ≥ 0.75** – nightly cron validates last 24 h queries.
*   **Legal‑hit accuracy ≥ 85 %** – `pytest test_benchmark.py` gate in CI.
*   **Trigger efficiency 10–20 %** – metric `sanad_trigger_ratio` alarms outside range.

## 5  App‑Flow Integration 

1.  **React Verify Page** `src/pages/Verify.tsx` → calls `POST /api/verify` with JSON { question }.

2.  **FastAPI** `verify.py` → injects Trace‑ID → hands off to `FlowController.run()`.

3.  **TriggerDetector** decides baseline vs Sanad;

    *   if baseline → call LLM → return.
    *   else proceed.

4.  **Retriever** fetches FAISS top‑k passages.

5.  **Draft Answer** via LLM.

6.  **Agents** (Integrity, Precision, Prov, Domain) evaluate in parallel via GPU streams.

7.  **Coordinator** computes weighted score; if < threshold, Enhancer prompts LLM with passages → new answer.

8.  **Prom Metrics** logged; JSON { answer, score, sources } returned to front‑end.

9.  **Front‑end** renders answer card, badge, drawer; user may submit feedback to `/api/feedback`.

## 6  Role‑Based Permissions 

|                          |                      |                           |                  |                      |
| ------------------------ | -------------------- | ------------------------- | ---------------- | -------------------- |
| Role                     | Git / Repo           | Prod API                  | Metrics          | Infrastructure       |
| **Owner**                | full                 | full                      | full             | full                 |
| **Org Admin**            | write app dirs       | read                      | read             | limited (scale pods) |
| **Verification Manager** | read                 | read/write verify weights | read             | –                    |
| **Curator**              | read docs, push data | –                         | –                | –                    |
| **Std User**             | none                 | call `/verify`            | personal history | –                    |
| **Auditor**              | read docs            | read GET `/audit`         | read             | –                    |

## 7  Open TODOs  

|       |                                                            |          |         |               |
| ----- | ---------------------------------------------------------- | -------- | ------- | ------------- |
| ID    | Task                                                       | Priority | Owner   | Due           |
| WS‑01 | Add ArgoCD sync‑wave labels to Helm chart                  | high     | DevOps  | Sprint 1 wk 2 |
| WS‑02 | Write ESLint custom rule to prevent hard‑coded hex colours | med      | FE Lead | Sprint 1 wk 2 |
| WS‑03 | Implement `/metrics/summary` back‑end endpoint             | high     | Backend | Sprint 1 wk 3 |
| WS‑04 | Setup Prom‑>Grafana provisioning in `ops/helm/grafana/`    | high     | DevOps  | Sprint 2 wk 5 |
| WS‑05 | **Enterprise Security Compliance**                         | **critical** | **Security** | **Sprint 1 wk 4** |
| WS‑06 | **License Compliance CI Integration**                      | **high** | **DevOps** | **Sprint 2 wk 1** |
| WS‑07 | **Disaster Recovery Automation**                           | **high** | **Backend** | **Sprint 2 wk 3** |

### 7.1 Enterprise Compliance Requirements

**Security Documentation:**
- `docs/SECURITY_RUNBOOK.md` - Incident response procedures, pager duty flows
- `docs/THREAT_MODEL.md` - STRIDE analysis with Islamic methodology specific threats
- Annual external penetration testing (milestone M8 at D+85)

**Data Protection:**
- GDPR Article 17 right-to-erasure implementation
- 180-day default retention with user-driven deletion
- PII detection and masking in query logs
- Encrypted backups with off-device key vault

**Operational Assurance:**
- RPO <1hr, RTO <2hr disaster recovery objectives  
- Automated nightly S3 snapshots of FAISS indices and SQLite
- Cost monitoring with 80% budget alerts
- OSS license scanning (MIT/BSD/Apache whitelist only)

**Islamic Methodology Protection:**
- Digital signatures for scholarly evaluations
- Immutable audit trails for grading changes
- Cultural authenticity monitoring and alerts
- Competitive intelligence protection measures

## 8  Islamic ʿIlm al-Rijāl Methodology Enhancement

### 8.1 Overview

**Objective:** Transform Sanad from simple weighted scoring to authentic 1,400-year Islamic scholarly evaluation methodology using a bolt-on upgrade approach that preserves existing architecture.

**Strategy:** Layer sophisticated Islamic evaluation engines onto current agent framework without breaking existing APIs or UI components.

### 8.2 Current vs Enhanced System

**Current Simple System:**
```python
# Simple weighted scoring
sanad_score = 0.4*integrity + 0.3*precision + 0.2*provenance + 0.1*domain
# Binary decision: score >= 0.70 ? pass : enhance
```

**Enhanced Islamic System:**
```python
# Traditional Islamic grading with sophisticated evaluation
grade = "THIQAH_THABIT"  # ثقة ثبت
certainty_factor = 0.9   # From consensus building
final_score = core_score * certainty_factor
# Conditional assessments based on context
```

### 8.3 Data Model Extensions

#### 8.3.1 Islamic Grading Constants (`backend/constants/grading.py`)

```python
GRADE_ORDER = [
    "THIQAH_THABIT",    # ثقة ثبت - Extremely reliable and precise
    "THIQAH",           # ثقة - Reliable
    "SADUQ",            # صدوق - Truthful/honest
    "LA_BASH_BIHI",     # لا بأس به - No problem with him
    "SALIH_AL_HADITH",  # صالح الحديث - Acceptable in hadith
    "LAYYIN",           # لين - Weak/soft
    "FIHI_NAZAR",       # فيه نظر - There is doubt about him
    "DAIF",             # ضعيف - Weak
    "MATRUK",           # متروك - Abandoned
    "KADHDHAB"          # كذاب - Liar
]

GRADE_SCORE = {g: 1 - i * 0.12 for i, g in enumerate(GRADE_ORDER)}

TEMPORAL_PATTERNS = [
    "EARLY_CAREER_STRONG",     # قوي في أول أمره
    "LATER_CAREER_WEAK",       # ضعف في آخر عمره
    "CONSISTENT_THROUGHOUT",   # ثابت طوال حياته
    "POLITICAL_PRESSURE_AFFECTED"  # تأثر بالضغوط السياسية
]
```

#### 8.3.2 SQLite Schema Extensions

```sql
-- Source profile table for Islamic evaluation
CREATE TABLE scholarly_grade (
    source_id TEXT PRIMARY KEY,
    overall_grade TEXT NOT NULL,
    domain_grades JSON,           -- {"medical": "THIQAH", "legal": "SADUQ"}
    reliable_when JSON,           -- ["SupremeCourt", "WHO"]
    unreliable_when JSON,         -- ["UnreviewedBlog", "SocialMedia"]
    temporal_pattern TEXT,        -- "EARLY_CAREER_STRONG"
    evaluation_date DATE,
    evaluating_scholars JSON      -- ["Scholar1", "Scholar2"]
);

-- Temporal reliability tracking
CREATE TABLE temporal_reliability (
    source_id TEXT,
    start_date DATE,
    end_date DATE,
    grade_delta INTEGER,          -- -1 = drop one level, +1 = improve
    reason TEXT,
    PRIMARY KEY (source_id, start_date)
);
```

#### 8.3.3 YAML Fixture Data (`backend/fixtures/islamic_profiles.yaml`)

```yaml
scholarly_profiles:
  labour_law:
    overall_grade: "THIQAH_THABIT"
    domain_grades:
      legal: "THIQAH_THABIT"
      medical: "FIHI_NAZAR"
    reliable_when: ["OfficialGazette", "MinistryOfLabour"]
    unreliable_when: ["UnofficialTranslation"]
    temporal_pattern: "CONSISTENT_THROUGHOUT"
    
  research_q5_2021:
    overall_grade: "SADUQ"
    domain_grades:
      economic: "THIQAH"
      social: "SADUQ"
    reliable_when: ["PeerReviewed", "GovernmentData"]
    unreliable_when: ["PrePrint", "UnverifiedSurvey"]
    temporal_pattern: "LATER_CAREER_WEAK"
```

### 8.4 Islamic Evaluation Engines

#### 8.4.1 ConditionalReliabilityEngine

```python
class ConditionalReliabilityEngine:
    """
    Implements conditional reliability assessment from Islamic methodology
    Sources can be reliable from some narrators, unreliable from others
    """
    
    def adjust_grade(self, base_grade: str, source_profile: dict, context: dict) -> str:
        """
        Adjust grade based on conditional reliability rules
        
        Args:
            base_grade: Starting Islamic grade
            source_profile: Source reliability profile
            context: Current evaluation context (producer, domain, etc.)
            
        Returns:
            Adjusted Islamic grade
        """
        producer = context.get("producer", "")
        domain = context.get("domain", "")
        
        # Check unreliable_when conditions
        if producer in source_profile.get("unreliable_when", []):
            return "DAIF"
            
        # Check domain-specific grading
        if domain in source_profile.get("domain_grades", {}):
            return source_profile["domain_grades"][domain]
            
        return base_grade
```

#### 8.4.2 TemporalReliabilitySystem

```python
class TemporalReliabilitySystem:
    """
    Implements temporal reliability tracking from Islamic methodology
    Narrator reliability can change over time
    """
    
    def adjust_for_time(self, grade: str, source_id: str, evaluation_date: datetime) -> str:
        """
        Adjust grade based on temporal reliability patterns
        
        Args:
            grade: Current Islamic grade
            source_id: Source identifier
            evaluation_date: When this evaluation is happening
            
        Returns:
            Time-adjusted Islamic grade
        """
        profile = self.get_source_profile(source_id)
        pattern = profile.get("temporal_pattern")
        
        if pattern == "LATER_CAREER_WEAK":
            # Check if source is old enough to be affected
            source_age = self.calculate_source_age(source_id, evaluation_date)
            if source_age > timedelta(days=730):  # 2 years
                return self.downgrade_grade(grade, 1)
                
        elif pattern == "EARLY_CAREER_STRONG":
            # Recent sources get boost
            source_age = self.calculate_source_age(source_id, evaluation_date)
            if source_age < timedelta(days=365):  # 1 year
                return self.upgrade_grade(grade, 1)
                
        return grade
```

#### 8.4.3 SourceNetworkAnalyzer

```python
class SourceNetworkAnalyzer:
    """
    Implements network validation from Islamic methodology
    Multiple independent sources strengthen reliability
    """
    
    def calculate_network_support(self, claim: str, passages: List[Passage]) -> float:
        """
        Calculate network support for a claim across multiple sources
        
        Args:
            claim: The claim being evaluated
            passages: Retrieved passages supporting the claim
            
        Returns:
            Network support factor (0.0 to 1.0)
        """
        # Group passages by independent sources
        source_groups = self.group_by_independent_sources(passages)
        
        # Count high-quality independent confirmations
        high_quality_confirmations = 0
        for group in source_groups:
            if self.has_high_quality_confirmation(group, claim):
                high_quality_confirmations += 1
        
        # Islamic methodology: 2+ independent high-quality sources = strong
        if high_quality_confirmations >= 2:
            return 0.9
        elif high_quality_confirmations == 1:
            return 0.7
        else:
            return 0.5
```

### 8.5 Enhanced Agent Integration

#### 8.5.1 Updated IntegrityAgent

```python
class IntegrityAgent(BaseAgent):
    """
    Enhanced IntegrityAgent with Islamic grading methodology
    """
    
    def __init__(self):
        super().__init__("IntegrityAgent")
        self.conditional_engine = ConditionalReliabilityEngine()
        self.temporal_engine = TemporalReliabilitySystem()
        
    async def evaluate(self, input_data: AgentInput) -> AgentScore:
        """
        Evaluate using sophisticated Islamic methodology
        """
        # Step 1: Basic similarity assessment (existing)
        base_score = self.calculate_base_similarity(input_data)
        
        # Step 2: Convert to Islamic grade
        base_grade = self.score_to_grade(base_score)
        
        # Step 3: Apply conditional reliability
        adjusted_grade = self.conditional_engine.adjust_grade(
            base_grade,
            self.get_source_profile(input_data.passages[0].doc_id),
            {"domain": "legal", "producer": "government"}
        )
        
        # Step 4: Apply temporal adjustment
        final_grade = self.temporal_engine.adjust_for_time(
            adjusted_grade,
            input_data.passages[0].doc_id,
            datetime.now()
        )
        
        # Step 5: Convert back to numerical score for coordination
        final_score = GRADE_SCORE[final_grade]
        
        return AgentScore(
            score=final_score,
            grade=final_grade,  # New field
            explanation=f"Islamic evaluation: {final_grade} based on source reliability assessment",
            confidence=0.85,
            agent_name=self.name
        )
```

### 8.6 Scholarly Consensus Implementation

#### 8.6.1 ConsensusEngine

```python
class ScholarlyConsensusEngine:
    """
    Implements ijmāʿ (scholarly consensus) building from Islamic methodology
    """
    
    def calculate_certainty_factor(self, agent_evaluations: List[AgentScore]) -> float:
        """
        Calculate certainty based on agent agreement (ijmāʿ simulation)
        
        Args:
            agent_evaluations: Evaluations from all agents
            
        Returns:
            Certainty factor (0.0 to 1.0)
        """
        # Extract grades from agents that provide them
        grades = [eval.grade for eval in agent_evaluations if hasattr(eval, 'grade')]
        
        if not grades:
            return 0.7  # Default uncertainty
            
        # Calculate agreement level
        unique_grades = set(grades)
        
        if len(unique_grades) == 1:
            # Unanimous agreement (ijmāʿ)
            return 0.95
        elif len(unique_grades) == 2:
            # Majority with minority opinion
            return 0.8
        else:
            # Significant disagreement
            return 0.6
    
    def determine_majority_grade(self, agent_evaluations: List[AgentScore]) -> str:
        """
        Determine the majority grade across agents
        """
        grades = [eval.grade for eval in agent_evaluations if hasattr(eval, 'grade')]
        
        if not grades:
            return "SADUQ"  # Default moderate grade
            
        # Return most common grade
        from collections import Counter
        grade_counts = Counter(grades)
        return grade_counts.most_common(1)[0][0]
```

### 8.7 Updated Coordinator Logic

```python
class EnhancedCoordinator:
    """
    Enhanced coordinator with Islamic consensus building
    """
    
    def __init__(self):
        self.consensus_engine = ScholarlyConsensusEngine()
        
    def compute_sanad_score(self, agent_evaluations: List[AgentScore]) -> dict:
        """
        Compute enhanced Sanad score with Islamic methodology
        """
        # Step 1: Traditional weighted scoring
        weights = {"integrity": 0.4, "precision": 0.3, "provenance": 0.2, "domain": 0.1}
        core_score = sum(weights[agent.agent_name.lower()] * agent.score 
                        for agent in agent_evaluations)
        
        # Step 2: Calculate certainty factor from consensus
        certainty_factor = self.consensus_engine.calculate_certainty_factor(agent_evaluations)
        
        # Step 3: Determine majority grade
        majority_grade = self.consensus_engine.determine_majority_grade(agent_evaluations)
        
        # Step 4: Final score with certainty multiplication
        final_score = core_score * certainty_factor
        
        return {
            "sanad_score": final_score,
            "grade": majority_grade,                    # New field
            "certainty": certainty_factor,              # New field
            "consensus_level": len(set(e.grade for e in agent_evaluations if hasattr(e, 'grade'))),  # New field
            "scholarly_justification": f"Grade {majority_grade} with {certainty_factor:.1%} certainty based on agent consensus"  # New field
        }
```

### 8.8 API Response Enhancement

#### 8.8.1 Extended VerificationResponse

```python
class VerificationResponse(BaseModel):
    """
    Enhanced response with Islamic methodology fields
    """
    answer: str
    sanad_score: float
    sources: List[Passage]
    processing_time_ms: int
    
    # New Islamic methodology fields (optional for backward compatibility)
    grade: Optional[str] = None                    # e.g., "THIQAH_THABIT"
    certainty: Optional[float] = None              # 0.0 to 1.0
    consensus_level: Optional[int] = None          # Number of unique grades
    scholarly_justification: Optional[str] = None # Explanation
    conditional_assessments: Optional[List[str]] = None  # Context-dependent notes
```

### 8.9 Frontend Enhancement

#### 8.9.1 Islamic Grade Display

```tsx
// Enhanced response display with Islamic grades
function ResponseCard({ response }: { response: VerificationResponse }) {
  return (
    <div className="response-card">
      <div className="answer">{response.answer}</div>
      
      {/* Enhanced badge with Islamic grade */}
      <Badge 
        tone={getToneFromGrade(response.grade)} 
        label={response.grade ? getArabicGrade(response.grade) : `${response.sanad_score:.2f}`}
      />
      
      {/* Certainty tooltip */}
      {response.certainty && (
        <Tooltip content={`Confidence: ${Math.round(response.certainty * 100)}%`}>
          <InfoIcon />
        </Tooltip>
      )}
      
      {/* Sources with grades */}
      <SourcesDrawer sources={response.sources} />
    </div>
  );
}

function getArabicGrade(grade: string): string {
  const gradeMap = {
    "THIQAH_THABIT": "ثقة ثبت",
    "THIQAH": "ثقة",
    "SADUQ": "صدوق",
    "LA_BASH_BIHI": "لا بأس به",
    "LAYYIN": "لين",
    "FIHI_NAZAR": "فيه نظر",
    "DAIF": "ضعيف"
  };
  return gradeMap[grade] || grade;
}
```

### 8.10 Implementation Timeline

| Task | Duration | Dependencies | Deliverable |
|------|----------|--------------|-------------|
| **BE-12.1-12.4**: Data model & fixtures | 0.5 days | None | SQLite tables, YAML seeder |
| **BE-13.1-13.3**: IntegrityAgent enhancement | 0.5 days | BE-12 | Islamic grading output |
| **BE-14.1-14.4**: Evaluation engines | 1.0 days | BE-12, BE-13 | Conditional & temporal logic |
| **BE-15.1-15.4**: Consensus implementation | 0.5 days | BE-14 | Scholarly consensus engine |
| **FE-09.1-09.4**: UI enhancements | 0.25 days | BE-15 | Arabic grade display |
| **QA-05.1-05.4**: Testing & validation | 0.5 days | All above | Test coverage & benchmarks |

**Total: 3.25 development days**

### 8.11 Validation Criteria

1. **Accuracy Improvement**: ≥3-5 percentage points over baseline
2. **Latency Impact**: <1ms overhead for Islamic evaluation
3. **Backward Compatibility**: All existing APIs continue working
4. **Cultural Authenticity**: Islamic scholarly validation of methodology
5. **Competitive Moat**: Complexity assessment confirms replication difficulty

*End of .windsurfrules – maintainers MUST update version & date on any schema‑level change.*
