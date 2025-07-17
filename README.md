# Sanad v2 - Islamic Knowledge Verification System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.0%2B-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue.svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-Private-red.svg)]()

> **Sanad** (سند) - An enterprise-grade Islamic knowledge verification system that enhances AI responses with rigorous fact-checking, source attribution, and Islamic scholarly methodology validation.

## 🌟 Overview

Sanad v2 is a comprehensive AI-powered system designed to verify and enhance responses to Islamic knowledge queries. Built on the principles of **ʿIlm al-Rijāl** (Islamic science of narrator criticism), it provides enterprise-grade verification, audit trails, and regulatory compliance for Islamic educational and research institutions.

### Key Features

- **🔍 Intelligent Trigger Detection**: Semantic analysis to determine when verification is needed
- **🤖 Multi-Agent Verification**: Specialized agents for integrity, precision, provenance, and domain expertise
- **📚 FAISS-Powered Retrieval**: GPU-accelerated document search with semantic similarity
- **🔒 Enterprise Security**: JWT authentication, rate limiting, GDPR compliance, and audit trails
- **📊 Real-time Monitoring**: Prometheus metrics, structured logging, and performance tracking
- **🌐 Modern Architecture**: FastAPI backend with React TypeScript frontend

## 🏗️ Architecture

```mermaid
graph TB
    A[User Query] --> B[FastAPI Gateway]
    B --> C[Trigger Detection]
    C --> D{Verification Needed?}
    D -->|Yes| E[FAISS Retrieval]
    D -->|No| F[Baseline LLM]
    E --> G[Agent Coordinator]
    G --> H[Integrity Agent]
    G --> I[Precision Agent]
    G --> J[Provenance Agent]
    G --> K[Domain Agent]
    H --> L[Score Aggregation]
    I --> L
    J --> L
    K --> L
    L --> M{Score < Threshold?}
    M -->|Yes| N[Response Enhancement]
    M -->|No| O[Original Response]
    N --> P[Audit Logging]
    O --> P
    F --> P
    P --> Q[User Response]
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- CUDA-capable GPU (recommended for FAISS)
- PostgreSQL 13+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/albarami/Sanad.git
   cd Sanad
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp config/env.template .env
   # Edit .env with your API keys and database settings
   ```

4. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   ```

5. **Initialize the database**
   ```bash
   # Run database migrations (implementation pending)
   python -m backend.db.init_db
   ```

### Running the Application

1. **Start the backend**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📖 Usage

### Basic Query

```python
import requests

# Basic query without verification
response = requests.post(
    "http://localhost:8000/api/v2/baseline",
    json={"question": "What is the ruling on prayer times?"}
)

# Enhanced query with Sanad verification
response = requests.post(
    "http://localhost:8000/api/v2/verify",
    json={"question": "What is the ruling on prayer times?"}
)
```

### CLI Tool

```bash
# Run verification from command line
python scripts/cli_verify.py "What are the conditions for valid wudu?"
```

## 🔧 Configuration

### Domain-Agnostic Design

Sanad v2 is designed to be **domain-agnostic** and can be easily adapted to different knowledge domains by simply changing configuration files - no code changes required!

#### Switching Domains

To switch to a different domain, update the `domain` section in `config/config.yaml` or use one of the pre-configured domain files:

```bash
# Use healthcare domain
cp config/domains/healthcare.yaml config/config.yaml

# Use finance domain  
cp config/domains/finance.yaml config/config.yaml

# Use labor market domain
cp config/domains/labor_market.yaml config/config.yaml
```

#### Domain Configuration Structure

```yaml
domain:
  name: "healthcare"  # Domain identifier
  keywords:  # Keywords for domain relevance detection
    - "medical"
    - "health"
    - "diagnosis"
    - "treatment"
    - "patient"
  enhancement_instructions: |
    6. For medical topics, prioritize peer-reviewed sources and clinical guidelines
    7. Use appropriate medical terminology and cite relevant studies
  terminology_guidelines: "Use standard medical terminology"
  source_requirements: "Prefer peer-reviewed medical journals"
```

#### Available Domain Examples

- **Islamic Knowledge** (`config/domains/islamic.yaml`): Default Islamic scholarly verification
- **Healthcare** (`config/domains/healthcare.yaml`): Medical and clinical knowledge
- **Finance** (`config/domains/finance.yaml`): Financial regulations and compliance
- **Labor Market** (`config/domains/labor_market.yaml`): Employment and labor law
- **General** (`config/domains/general.yaml`): General-purpose knowledge verification

### Advanced Features

#### Hot-Reload Configuration

The system supports hot-reloading of configuration without restart:

```python
from core.enhancer import ResponseEnhancer

# Initialize enhancer
enhancer = ResponseEnhancer()

# Reload configuration at runtime
enhancer.reload_config()  # Reloads from file
# or
enhancer.reload_config(new_config)  # Use specific config
```

#### Production Resilience Features

- **Jittered Retry Backoff**: LLM calls use exponential backoff with ±20% jitter to prevent thundering herd
- **Config Caching**: Avoids per-call YAML parsing for better performance
- **LLM Client Injection**: Constructor accepts optional LLM client for enhanced testability
- **Token Budgeting**: Automatic passage truncation to prevent token limit issues
- **Case-Insensitive Matching**: All agent and keyword comparisons are case-safe

#### Environment Variables

```bash
# Override domain configuration
SANAD_DOMAIN_CONFIG=./config/domains/healthcare.yaml

# API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/sanad
```

### Core Configuration

Key configuration options in `config/config.yaml`:

```yaml
llm:
  provider: "openai"  # or "anthropic"
  model: "gpt-4"
  temperature: 0.1

agents:
  weights:
    integrity: 0.30
    precision: 0.25
    provenance: 0.25
    domain: 0.20
  
retrieval:
  top_k: 10
  similarity_threshold: 0.7
  use_gpu: true

performance:
  target_latency_ms: 800
  max_concurrent_requests: 100
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Generate coverage report
pytest --cov=backend tests/
```

## 📊 Monitoring

- **Metrics**: Prometheus metrics available at `/metrics`
- **Health Check**: `/health` endpoint for system status
- **Logs**: Structured JSON logging with configurable levels
- **Audit Trail**: Complete request/response logging for compliance

## 🔒 Security

- **Authentication**: JWT-based with configurable expiration
- **Rate Limiting**: Configurable per-user and global limits
- **GDPR Compliance**: Data retention policies and user data deletion
- **Audit Logging**: Complete audit trail for all operations
- **Input Validation**: Comprehensive request validation and sanitization

## 📚 Documentation

- [**Project Requirements**](docs/project_requirements_document.md) - Comprehensive requirements and specifications
- [**Implementation Plan**](docs/implementation_plan.md) - Technical implementation roadmap
- [**Security Guidelines**](docs/security_guideline_document.md) - Security architecture and controls
- [**API Documentation**](docs/frontend_guidelines_document.md) - Frontend and API guidelines
- [**Threat Model**](docs/THREAT_MODEL.md) - Security threat analysis
- [**Security Runbook**](docs/SECURITY_RUNBOOK.md) - Incident response procedures

## 🛣️ Roadmap

### Current Sprint
- [ ] Implement missing `enhancer` module
- [ ] Add comprehensive test suite
- [ ] Set up CI/CD pipeline
- [ ] Container deployment setup

### Upcoming Features
- [ ] Advanced Islamic ʿIlm al-Rijāl methodology integration
- [ ] Multi-language support (Arabic, English)
- [ ] Advanced analytics dashboard
- [ ] Mobile application
- [ ] Kubernetes deployment

## 🤝 Contributing

This is a private repository. For internal contributors:

1. Create a feature branch from `main`
2. Follow the coding standards in `docs/implementation_plan.md`
3. Add tests for new functionality
4. Update documentation as needed
5. Submit a pull request for review

## 📄 License

This project is proprietary and confidential. All rights reserved.

## 🆘 Support

For technical support and questions:
- Create an issue in this repository
- Contact the development team
- Review the comprehensive documentation in the `docs/` directory

---

**Built with ❤️ for the Islamic knowledge community**