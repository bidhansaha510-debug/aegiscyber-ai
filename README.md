<div align="center">

# AegisCyber AI

### AI-Powered Cybersecurity Research, Reconnaissance, OSINT & APT Simulation Platform

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![PySide6](https://img.shields.io/badge/PySide6-Desktop_GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MITRE ATT&CK](https://img.shields.io/badge/MITRE-ATT%26CK-red?style=for-the-badge)](https://attack.mitre.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<p align="center">
A production-grade, fully local, modular desktop application that uses AI to plan, validate, execute, parse, and analyze cybersecurity operations — with APT-grade stealth capabilities, OPSEC awareness, Living-off-the-Land support, and MITRE ATT&CK integration.
</p>

---

**No cloud. No telemetry. No API keys required for core functionality.**  
Everything runs on your machine with Ollama + local models.

</div>

---

## Table of Contents

- [What is AegisCyber AI?](#what-is-aegiscyber-ai)
- [Key Features](#key-features)
- [APT & Stealth Capabilities](#apt--stealth-capabilities)
- [Architecture](#architecture)
- [The 10-Stage Pipeline](#the-10-stage-pipeline)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How to Use](#how-to-use)
- [Stealth Mode](#stealth-mode)
- [Tool Registry](#tool-registry)
- [OSINT Engine](#osint-engine)
- [Security & Safety](#security--safety)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Extending AegisCyber](#extending-aegiscyber)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## What is AegisCyber AI?

**AegisCyber AI** is a local AI-powered cybersecurity assistant designed for authorized security research and advanced adversary simulation. It combines a local large language model (via Ollama) with a structured execution pipeline to help security professionals with:

- **Reconnaissance & Enumeration** — Automated network, DNS, web, and service discovery
- **OSINT Intelligence** — Multi-source open-source intelligence gathering with knowledge graph correlation
- **Vulnerability Assessment** — Guided scanning with structured analysis
- **APT Simulation & Red Teaming** — Stealth-aware operations with OPSEC scoring, LOLBin support, and MITRE ATT&CK kill chain tracking
- **CTF & Cyber Range Support** — Intelligent tool selection and result interpretation
- **Security Research** — Evidence-based analysis with conclusion verification

Unlike a simple chatbot wrapper, AegisCyber AI implements a **10-stage pipeline** with strict separation of concerns: the LLM *plans* and *analyzes* but **never directly executes** commands. Every command passes through policy validation, risk classification, OPSEC evaluation, and (optionally) user approval before execution.

---

## Key Features

### AI-Powered Intelligence
- **Task Decomposition** — Natural language requests are broken into structured, phased task plans with automatic dependency resolution
- **Smart Tool Selection** — AI-assisted + deterministic scoring to pick the best tool for each task
- **Result Analysis** — Structured parsing followed by AI-powered security analysis
- **Conclusion Verification** — Independent verification that conclusions are supported by evidence
- **Conversation Memory** — Context-aware multi-turn interactions with investigation state

### 25+ Integrated Security Tools
Pre-configured definitions for: `nmap`, `masscan`, `nikto`, `gobuster`, `ffuf`, `sqlmap`, `nuclei`, `amass`, `subfinder`, `httpx`, `dnsx`, `dig`, `whois`, `curl`, `enum4linux`, `john`, `hashcat`, `hydra`, `tshark`, `tcpdump`, `metasploit`, `wireshark`, `responder`, `netcat`, `wget`

### OSINT Engine with Knowledge Graph
- **6 Connectors**: DNS resolution, WHOIS, crt.sh (Certificate Transparency), GitHub, URLScan.io, Shodan
- **NetworkX Knowledge Graph** — Entity & relationship tracking with graph traversal and subgraph extraction
- **Automatic Correlation** — Cross-source entity deduplication and relationship mapping

### Security-First Design
- **Scope-based Authorization** — Only targets within the defined scope are allowed
- **Policy Engine** — Risk classification (SAFE to BLOCKED), dangerous argument detection, executable blocklists
- **Approval Gates** — Medium/High risk commands require explicit user approval
- **Kill Switch** — Instant termination of all running processes
- **Full Audit Trail** — Every action logged in structured JSONL format

### Desktop GUI + REST API
- **PySide6 Desktop App** — Dark cybersecurity-themed GUI with live AI reasoning panel and GPU telemetry
- **FastAPI Server** — 12 REST endpoints for programmatic access
- **Multi-Backend Execution** — Native Windows, WSL2 (Kali), and Docker support

---

## APT & Stealth Capabilities

AegisCyber AI includes a full **APT-grade stealth layer** designed for realistic adversary simulation and red team operations. Toggle **◉ STEALTH** mode in the GUI header to activate.

### Stealth & OPSEC Engine (`app/stealth/`)

| Component | What It Does |
|-----------|-------------|
| **OPSEC Engine** | Assigns a risk score (0-100) to every command before execution. Factors in signature detectability, traffic volume, log footprint, and timing profile. |
| **EDR Detection Matrices** | Estimates detection probability against 5 SOC stacks: CrowdStrike, SentinelOne, Elastic SIEM, Splunk ES, and Microsoft Defender. |
| **Stealth Alternatives** | When a noisy tool is selected (e.g., `nmap -sV` → OPSEC 100/COMPROMISED), automatically suggests stealthier alternatives (e.g., `curl` → OPSEC 12/GHOST). |
| **Traffic Profiler** | Jitter injection (randomized delays), request rate limiting, business-hours awareness, and port scan fragmentation. 4 pre-built profiles: `paranoid`, `careful`, `normal`, `aggressive`. |
| **Signature Evader** | Maintains a database of known IDS/WAF signatures per tool and automatically applies evasion flags (`--randomize-hosts`, `--data-length`, `-f`, `-D RND:5`, `-T2`, etc.). |

### Living-off-the-Land Engine (`app/lolbin/`)

APTs rarely use `nmap` or `gobuster`. They use what's already on the target.

- **24 Curated LOLBins** — Linux (GTFOBins) + Windows (LOLBAS) native binaries mapped to offensive tasks
- **Task Resolution** — Given a task like "port scan", resolves to `bash /dev/tcp` (stealth=95) instead of `nmap` (COMPROMISED)
- **Categories**: Recon, Download, Execute, Persist, Exfiltrate, Privilege Escalation
- **Each entry includes**: binary name, example commands, stealth rating, MITRE ATT&CK technique IDs, detection notes

**Example LOLBins:**

| Binary | Platform | Stealth | Use Case |
|--------|----------|---------|----------|
| `bash /dev/tcp` | Linux | 95/100 | Port scanning without any tool installation |
| `openssl s_client` | Cross | 90/100 | TLS probing that looks like normal HTTPS |
| `curl` | Cross | 85/100 | HTTP probing indistinguishable from web traffic |
| `find` | Linux | 92/100 | SUID binary discovery for privilege escalation |
| `certutil` | Windows | 55/100 | File download via certificate utility |
| `bitsadmin` | Windows | 65/100 | Async file transfer blending with Windows Update |

### MITRE ATT&CK Integration (`app/mitre/`)

- **Automatic Technique Mapping** — Every tool execution is tagged with ATT&CK tactic/technique IDs (e.g., `nmap` → T1046 Network Service Discovery)
- **Kill Chain Tracking** — Visualize which ATT&CK phases have been covered across an investigation
- **Phase Progression** — AI suggests the next logical kill chain phase based on current coverage
- **Navigator Export** — Export ATT&CK Navigator JSON layers for import into MITRE's official visualization tool
- **Coverage Analytics** — Track tactics covered, techniques completed, and overall kill chain progress

### OPSEC-Aware Pipeline

When stealth mode is active, the entire pipeline transforms:

| Stage | Standard Mode | Stealth Mode |
|-------|--------------|-------------|
| **Planning** | Direct tool execution | Passive-first, LOLBin-preferred, OPSEC cooldown phases inserted |
| **Tool Selection** | Best capability match | OPSEC penalty on noisy tools, stealth alternatives suggested |
| **Command Building** | Standard flags | Evasion flags auto-applied (randomization, padding, timing) |
| **Execution** | Immediate | Jitter delays between operations, rate limiting enforced |
| **Blocking** | Policy-based only | Commands exceeding OPSEC threshold (default: 70) are blocked |
| **Tracking** | Basic logging | MITRE ATT&CK technique IDs recorded for every execution |

---

## Architecture

```
+---------------------------------------------------------------------+
|                        PySide6 GUI / FastAPI                        |
|  [◉ STEALTH] [Target Scope] [Kill Switch]                          |
+---------------------------------------------------------------------+
|                         ORCHESTRATOR                                |
|  +----------+ +--------+ +---------+ +----------+ +------------+  |
|  | Planner  | | Router | | Analyst | | Verifier | |   Memory   |  |
|  +----+-----+ +---+----+ +----+----+ +----+-----+ +------------+  |
|       |           |           |           |                       |
|  +----v-----------v-----------v-----------v-----------------+    |
|  |                    Ollama Client (Local LLM)              |    |
|  +----------------------------------------------------------+    |
+---------------------------------------------------------------------+
|  TOOL LAYER          |  SECURITY LAYER        |  DATA LAYER        |
|  +----------------+  |  +------------------+  |  +--------------+ |
|  | Tool Registry  |  |  | Policy Engine    |  |  | Parser       | │
|  | (25 YAML defs) |  |  | Authorization    |  |  | Registry     | │
|  | Discovery      |  |  | Audit Logger     |  |  | OSINT Engine | │
|  | Command Planner|  |  | Kill Switch      |  |  | Knowledge    | │
|  | Scoring Engine |  |  | Secrets Vault    |  |  | Graph        | │
|  +----------------+  |  +------------------+  |  +--------------+ │
+---------------------------------------------------------------------+
|  STEALTH LAYER       |  LOLBIN LAYER          |  ATT&CK LAYER     |
|  +----------------+  |  +------------------+  |  +--------------+ |
|  | OPSEC Engine   |  |  | LOLBin Engine    |  |  | ATT&CK       | |
|  | Traffic Profiler|  |  | LOLBin Registry |  |  | Mapper       | |
|  | Sig. Evader    |  |  | (24 LOLBins)     |  |  | Navigator    | |
|  | EDR Matrices   |  |  | Task Resolver    |  |  | Kill Chain   | |
|  +----------------+  |  +------------------+  |  +--------------+ |
+---------------------------------------------------------------------+
|                      EXECUTION BACKENDS                             |
|  +--------------+  +--------------+  +--------------+              |
|  |   Native     |  |    WSL2      |  |   Docker     |              |
|  |  (Windows)   |  | (Kali Linux) |  |  (Kali img)  |              |
|  +--------------+  +--------------+  +--------------+              |
+---------------------------------------------------------------------+
|                    SQLite Database (aiosqlite)                       |
+---------------------------------------------------------------------+
```

---

## The 10-Stage Pipeline

Every user request flows through these 10 strictly separated stages:

| # | Stage | Module | What Happens |
|---|-------|--------|--------------|
| 1 | **Natural Language Understanding** | `orchestrator.py` | Parse user intent, extract targets and goals |
| 2 | **Task Planning** | `planner.py` | Decompose request into phased plan with categories & risk levels. In stealth mode: passive-first ordering, OPSEC cooldown phases |
| 3 | **Tool/Engine Selection** | `router.py` | AI + deterministic scoring selects optimal tools. In stealth mode: OPSEC penalty on noisy tools, LOLBin alternatives preferred |
| 4 | **Command Generation** | `command_planner.py` | Build structured `CommandPlan` with validated arguments |
| 4.5 | **OPSEC Evaluation** *(stealth only)* | `opsec_engine.py` | Score command detection risk, block if above threshold, apply evasion flags |
| 5 | **Command Validation** | `policy.py` | Risk classify, check blocked patterns, verify scope authorization |
| 6 | **Sandboxed Execution** | `manager.py` + backends | Execute via Native/WSL2/Docker with concurrency limits. In stealth mode: jitter delays applied |
| 7 | **Result Collection** | `manager.py` | Capture stdout/stderr, exit codes, enforce timeouts |
| 8 | **Result Analysis** | `analyst.py` + parsers | Parse structured data (nmap XML, DNS records, etc.) then AI analysis |
| 9 | **OSINT Correlation** | `osint/engine.py` | Cross-reference findings across intelligence sources, build knowledge graph |
| 10 | **Response Generation** | `orchestrator.py` | Synthesize verified findings into a security report. ATT&CK techniques tagged |

---

## Requirements

### System Requirements
| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (64-bit) |
| **Python** | 3.12 or higher |
| **RAM** | 16 GB minimum |
| **GPU** | NVIDIA GPU (RTX series recommended for fast inference) |
| **Disk** | 10 GB free |

### Required Software
- **[Ollama](https://ollama.com)** with `llama3:latest` pulled
- **Python 3.12+**
- **WSL2 with Kali Linux** (recommended for full tool execution)

---

## Installation

```bash
git clone https://github.com/bidhansaha510-debug/aegiscyber-ai.git
cd aegiscyber-ai

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

ollama pull llama3:latest
```

---

## Quick Start

```bash
python -m app.main
```

Or launch the FastAPI server:

```bash
uvicorn app.api.server:app --host 127.0.0.1 --port 8741
```

---

## Stealth Mode

Click the **◉ STEALTH** button in the GUI header to engage stealth mode. When active:

1. **Planner** reorders phases: passive recon first → OPSEC cooldown gaps → active scans (low-and-slow)
2. **Router** applies OPSEC penalty to noisy tools and prefers LOLBin alternatives
3. **Signature Evader** auto-applies evasion flags to every command
4. **Traffic Profiler** injects randomized jitter delays between tool executions
5. **OPSEC Engine** blocks any command scoring above the threshold (default: 70/100)
6. **ATT&CK Mapper** tags every execution with MITRE technique IDs and tracks kill chain progress

### OPSEC Score Examples

| Command | OPSEC Score | Risk Label |
|---------|-------------|------------|
| `curl -s -I https://target/` | 12/100 | GHOST |
| `dig A target.com` | 10/100 | GHOST |
| `openssl s_client -connect target:443` | 10/100 | GHOST |
| `subfinder -d target.com` | 30/100 | LOW |
| `nmap -T2 --max-rate 10 target` | 50/100 | MODERATE |
| `gobuster dir -u target -w wordlist.txt` | 80/100 | LOUD |
| `nmap -sV -sC -A target` | 100/100 | COMPROMISED |
| `sqlmap -u target --batch` | 100/100 | COMPROMISED |

### Stealth Configuration

Configure in `app/config.py` → `StealthConfig`:

| Setting | Default | Description |
|---------|---------|-------------|
| `stealth_mode_default` | `False` | Start with stealth mode on |
| `opsec_threshold` | `70` | Block commands scoring above this |
| `traffic_profile` | `careful` | Jitter profile: `paranoid`, `careful`, `normal`, `aggressive` |
| `evasion_level` | `careful` | How aggressively to apply evasion flags |
| `prefer_lolbins` | `True` | Prefer LOLBins over signatured tools |
| `enable_mitre_tracking` | `True` | Track MITRE ATT&CK techniques |
| `fragment_large_scans` | `True` | Split large port scans into fragments |
| `respect_business_hours` | `True` | Operate during business hours for traffic blending |

---

## Project Structure

```
aegiscyber-ai/
├── app/
│   ├── ai/                     # AI pipeline
│   │   ├── orchestrator.py     # 10-stage execution pipeline
│   │   ├── planner.py          # Task decomposition (stealth-aware)
│   │   ├── router.py           # Tool selection (OPSEC-aware)
│   │   ├── analyst.py          # Result analysis
│   │   ├── verifier.py         # Conclusion verification
│   │   ├── memory.py           # Conversation context
│   │   ├── poc_generator.py    # Proof-of-Concept report generation
│   │   └── prompts/            # System prompts & task templates
│   ├── stealth/                # APT stealth layer
│   │   ├── opsec_engine.py     # OPSEC scoring, EDR matrices, alternatives
│   │   ├── traffic_profiler.py # Jitter, rate limiting, timing
│   │   └── signature_evader.py # IDS/WAF signature evasion
│   ├── lolbin/                 # Living-off-the-Land engine
│   │   ├── lolbin_engine.py    # Task → native binary resolver
│   │   └── lolbin_registry.yaml # 24 curated LOLBins (GTFOBins + LOLBAS)
│   ├── mitre/                  # MITRE ATT&CK integration
│   │   ├── attack_mapper.py    # Tool → technique mapping, kill chain
│   │   └── attack_navigator.py # ATT&CK Navigator JSON export
│   ├── execution/              # Sandboxed command execution
│   ├── gui/                    # PySide6 desktop GUI
│   ├── osint/                  # OSINT engine & connectors
│   ├── parsers/                # Tool output parsers
│   ├── security/               # Authorization, policy, audit, kill switch
│   ├── tools/                  # Tool registry, discovery, scoring
│   └── config.py               # Application configuration
├── tool_registry/              # 25 YAML tool definitions
└── requirements.txt
```

---

## Disclaimer

> **AegisCyber AI is designed for authorized security research, penetration testing, and red team operations only.**
>
> Users are solely responsible for ensuring they have proper authorization before using this tool against any target. Unauthorized access to computer systems is illegal. The developers assume no liability for misuse.
>
> The stealth and APT simulation features are designed to make authorized testing more realistic by emulating real-world adversary techniques. They do not bypass the scope authorization system — all operations still require targets to be within the authorized scope.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
