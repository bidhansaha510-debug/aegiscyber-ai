<div align="center">

# AegisCyber AI

### AI-Powered Cybersecurity Research, Reconnaissance & OSINT Assistant

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)](https://ollama.com)
[![PySide6](https://img.shields.io/badge/PySide6-Desktop_GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython-6/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST_API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

<p align="center">
A production-grade, fully local, modular desktop application that uses AI to plan, validate, execute, parse, and analyze cybersecurity operations — all within strict authorization boundaries.
</p>

---

**No cloud. No telemetry. No API keys required for core functionality.**  
Everything runs on your machine with Ollama + local models.

</div>

---

## Table of Contents

- [What is AegisCyber AI?](#what-is-aegiscyber-ai)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [The 10-Stage Pipeline](#the-10-stage-pipeline)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How to Use](#how-to-use)
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

**AegisCyber AI** is a local AI-powered cybersecurity assistant designed for authorized security research. It combines a local large language model (via Ollama) with a structured execution pipeline to help security professionals with:

- **Reconnaissance & Enumeration** — Automated network, DNS, web, and service discovery
- **OSINT Intelligence** — Multi-source open-source intelligence gathering with knowledge graph correlation
- **Vulnerability Assessment** — Guided scanning with structured analysis
- **CTF & Cyber Range Support** — Intelligent tool selection and result interpretation
- **Security Research** — Evidence-based analysis with conclusion verification

Unlike a simple chatbot wrapper, AegisCyber AI implements a **10-stage pipeline** with strict separation of concerns: the LLM *plans* and *analyzes* but **never directly executes** commands. Every command passes through policy validation, risk classification, and (optionally) user approval before execution.

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

## Architecture

```
+---------------------------------------------------------------------+
|                        PySide6 GUI / FastAPI                        |
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
| 2 | **Task Planning** | `planner.py` | Decompose request into phased plan with categories & risk levels |
| 3 | **Tool/Engine Selection** | `router.py` | AI + deterministic scoring selects optimal tools |
| 4 | **Command Generation** | `command_planner.py` | Build structured `CommandPlan` with validated arguments |
| 5 | **Command Validation** | `policy.py` | Risk classify, check blocked patterns, verify scope authorization |
| 6 | **Sandboxed Execution** | `manager.py` + backends | Execute via Native/WSL2/Docker with concurrency limits |
| 7 | **Result Collection** | `manager.py` | Capture stdout/stderr, exit codes, enforce timeouts |
| 8 | **Result Analysis** | `analyst.py` + parsers | Parse structured data (nmap XML, DNS records, etc.) then AI analysis |
| 9 | **OSINT Correlation** | `osint/engine.py` | Cross-reference findings across intelligence sources, build knowledge graph |
| 10 | **Response Generation** | `orchestrator.py` | Synthesize verified findings into a security report |

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
# 1. Clone the repository
git clone https://github.com/bidhansaha510-debug/aegiscyber-ai.git
cd aegiscyber-ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Pull the default Ollama model
ollama pull llama3:latest
```

---

## Quick Start

```bash
# Launch Desktop GUI
python -m app.main

# Or launch FastAPI server
uvicorn app.api.server:app --host 127.0.0.1 --port 8741
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
