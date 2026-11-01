# Network Assurance Copilot - Evaluation Report

**Benchmark Label:** `benchmark_run_50`  
**Dataset:** 50 simulated multi-domain incidents (RAN, Transport, Core)  
**Evaluation Timestamp:** 2026-11-01 14:11:28

## Key Outcome KPIs

| Outcome KPI | Manual Operations Baseline | Network Assurance Copilot | Operational Impact |
|---|---|---|---|
| **Incident Correlation** | 375 unbatched tickets | 97 triaged clusters | **74.1% ticket reduction** |
| **Noise Suppression** | 0% (alarm fatigue) | 53 chatter clusters | **100% flapping interface noise filtered** |
| **RCA Diagnostic Accuracy** | ~50-60% manual triage | **100.0%** (44/44) | **High-precision root cause isolation** |
| **Closed-Loop Automation** | 0.0% (manual approval) | **75.0%** autonomous | **Zero-touch remediation on low-risk faults** |
| **Mean Time to Resolution (MTTR)** | 45.0 minutes | **5.2 minutes** | **88.3% MTTR reduction** |

## Evaluation Design & Guardrails
- 50 incidents generated across Transport Link Down, Cell Congestion, Site Power Failure, Core Signaling Overload, and Interface Flapping.
- Ground truth was completely isolated; evaluation matched incidents post-hoc via temporal intersection.
- Auto-remediation was constrained to low-risk allowlisted actions with >=0.80 confidence.
