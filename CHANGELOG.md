# Changelog

## [v2.0.0-alpha.1] - 2025-07-18

### ✨ Features

- **Prometheus Metrics Endpoint (BE-19)**: Implemented a secure `/metrics` endpoint to expose key application metrics for monitoring. Includes custom metrics for response enhancement and a new `/healthz` endpoint for Kubernetes health probes.
- **Grafana Dashboards (BE-20)**: Added a pre-configured Grafana dashboard JSON for visualizing enhancement success rate, p95 latency, and RPS vs. error rate. The dashboard is configured for automatic import via Helm.
- **Configuration Immutability Hash (BE-21)**: Integrated a system to compute a SHA-256 hash of the `config/` directory on startup. The hash is exported as a Prometheus metric (`sanad_config_hash`) to monitor for unauthorized configuration changes.
- **CI Guard for Config Changes (BE-21)**: Added a shell script (`scripts/check_config_changes.sh`) to be used in CI pipelines to ensure that any changes to the configuration are documented in the changelog.

### 🐛 Bug Fixes

- **Module Import Paths**: Corrected relative import paths in `backend/core/enhancer.py` and `backend/coordinator/orchestrator.py` to resolve `ModuleNotFoundError` and `ImportError` on startup.
- **Prometheus Metric Registration**: Fixed a `ValueError` for duplicate metric registration during hot-reloading by ensuring metrics are only created if they don't already exist in the registry.
- **Environment Variable Loading**: Resolved an issue where the `SANAD_METRICS_PASSWORD` was not being loaded correctly by implementing `python-dotenv` to load variables from a `.env` file.
- **Database Shutdown Warning**: Fixed a `RuntimeWarning` during application shutdown by converting the `db_manager.close()` method to `async` and awaiting it correctly in the FastAPI lifespan manager.

### ⚙️ Housekeeping

- **Dependencies**: Updated `backend/requirements.txt` to include `python-dotenv` and other core dependencies for better environment management.
- **Task Board**: Updated `TASK.md` to reflect the completion of the sprint block (BE-19, BE-20, BE-21).

All notable changes to the Sanad v2 project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Prometheus metrics endpoint** with basic authentication (`/metrics`)
- **Kubernetes health probe endpoint** (`/healthz`) for container orchestration
- **Grafana dashboards** for enhancement metrics monitoring:
  - Enhancement Success Rate (stacked bar chart)
  - Enhancement p95 Latency (line chart)
  - RPS vs Error Rate (overlay chart for load testing)
- **Config immutability hash** system for tamper detection:
  - SHA-256 hash computation of `config/` directory at startup
  - Prometheus gauge `sanad_config_hash{hash="..."}` for monitoring
  - CI guard script to require CHANGELOG updates for config changes
- **Enhanced observability** with comprehensive metrics collection:
  - `sanad_enhancement_attempts_total` counter with status labels
  - `sanad_enhancement_duration_seconds` histogram for latency tracking

### Changed
- **FastAPI main.py** updated with Prometheus integration and config hash startup
- **TASK.md** updated with completed BE-19, BE-20, BE-21 tasks
- **Grafana deployment configuration** in `ops/grafana/values.yaml`

### Security
- **Metrics endpoint authentication** using `SANAD_METRICS_PASSWORD` environment variable
- **Config integrity monitoring** with hash-based tamper detection

## [2.0.0-alpha] - 2025-07-17

### Added
- **Domain-agnostic ResponseEnhancer** with YAML-driven configuration
- **Production-grade hardening** with retry logic, jitter, and hot-reload
- **Comprehensive test coverage** with 11 passing unit and integration tests
- **Enterprise observability** with Prometheus metrics hooks

### Changed
- **Enhancer module refactored** from Islamic-specific to domain-agnostic
- **Configuration system** now supports healthcare, finance, labor market, and other domains
- **Token budgeting** with 512-character passage truncation

### Fixed
- **Critical runtime bugs** including missing imports and case-sensitivity issues
- **Test failures** related to mock configurations and model validation
- **Enhancement logic** now properly handles LLM failures and timeouts

### Security
- **Config-driven retry parameters** prevent hardcoded values
- **Jittered exponential backoff** prevents thundering herd attacks
