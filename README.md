<div align="center">

# ⛨ AegisCyber AI

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

## 📋 Table of Contents

- [What is AegisCyber AI?](#-what-is-aegiscyber-ai)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [The 10-Stage Pipeline](#-the-10-stage-pipeline)
- [Screenshots](#-screenshots)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [How to Use](#-how-to-use)
- [Tool Registry](#-tool-registry)
- [OSINT Engine](#-osint-engine)
- [Security & Safety](#-security--safety)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Extending AegisCyber](#-extending-aegiscyber)
- [Disclaimer](#-disclaimer)
- [License](#-license)

---

## 🔍 What is AegisCyber AI?

**AegisCyber AI** is a local AI-powered cybersecurity assistant designed for authorized security research. It combines a local large language model (via Ollama) with a structured execution pipeline to help security professionals with:

- **Reconnaissance & Enumeration** — Automated network, DNS, web, and service discovery
- **OSINT Intelligence** — Multi-source open-source intelligence gathering with knowledge graph correlation
- **Vulnerability Assessment** — Guided scanning with structured analysis
- **CTF & Cyber Range Support** — Intelligent tool selection and result interpretation
- **Security Research** — Evidence-based analysis with conclusion verification

Unlike a simple chatbot wrapper, AegisCyber AI implements a **10-stage pipeline** with strict separation of concerns: the LLM *plans* and *analyzes* but **never directly executes** commands. Every command passes through policy validation, risk classification, and (optionally) user approval before execution.

---

## ✨ Key Features

### 🧠 AI-Powered Intelligence
- **Task Decomposition** — Natural language requests are broken into structured, phased task plans
- **Smart Tool Selection** — AI-assisted + deterministic scoring to pick the best tool for each task
- **Result Analysis** — Structured parsing followed by AI-powered security analysis
- **Conclusion Verification** — Independent verification that conclusions are supported by evidence
- **Conversation Memory** — Context-aware multi-turn interactions with investigation state

### 🔧 25+ Integrated Security Tools
Pre-configured YAML definitions for: `nmap`, `masscan`, `nikto`, `gobuster`, `ffuf`, `sqlmap`, `nuclei`, `amass`, `subfinder`, `httpx`, `dnsx`, `dig`, `whois`, `curl`, `enum4linux`, `john`, `hashcat`, `hydra`, `tshark`, `tcpdump`, `metasploit`, `wireshark`, `responder`, `netcat`, `wget`

### 🌐 OSINT Engine with Knowledge Graph
- **6 Connectors**: DNS resolution, WHOIS, crt.sh (Certificate Transparency), GitHub, URLScan.io, Shodan
- **NetworkX Knowledge Graph** — Entity & relationship tracking with graph traversal and subgraph extraction
- **Automatic Correlation** — Cross-source entity deduplication and relationship mapping

### 🛡️ Security-First Design
- **Scope-based Authorization** — Only targets within the defined scope are allowed
- **Policy Engine** — Risk classification (SAFE → BLOCKED), dangerous argument detection, executable blocklists
- **Approval Gates** — Medium/High risk commands require explicit user approval
- **Kill Switch** — Instant termination of all running processes
- **Full Audit Trail** — Every action logged in structured JSONL format

### 🖥️ Desktop GUI + REST API
- **PySide6 Desktop App** — Dark cybersecurity-themed GUI with live AI reasoning panel
- **FastAPI Server** — 12 REST endpoints for programmatic access
- **Multi-Backend Execution** — Native Windows, WSL2 (Kali), and Docker support

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PySide6 GUI / FastAPI                        │
├─────────────────────────────────────────────────────────────────────┤
│                         ORCHESTRATOR                                │
│  ┌──────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Planner  │ │ Router │ │ Analyst │ │ Verifier │ │   Memory   │  │
│  └────┬─────┘ └───┬────┘ └────┬────┘ └────┬─────┘ └────────────┘  │
│       │            │           │            │                       │
│  ┌────▼────────────▼───────────▼────────────▼─────────────────┐    │
│  │                    Ollama Client (Local LLM)                │    │
│  └─────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────┤
│  TOOL LAYER          │  SECURITY LAYER        │  DATA LAYER        │
│  ┌────────────────┐  │  ┌──────────────────┐  │  ┌──────────────┐ │
│  │ Tool Registry  │  │  │ Policy Engine    │  │  │ Parser       │ │
│  │ (25 YAML defs) │  │  │ Authorization    │  │  │ Registry     │ │
│  │ Discovery      │  │  │ Audit Logger     │  │  │ OSINT Engine │ │
│  │ Command Planner│  │  │ Kill Switch      │  │  │ Knowledge    │ │
│  │ Scoring Engine │  │  │ Secrets Vault    │  │  │ Graph        │ │
│  └────────────────┘  │  └──────────────────┘  │  └──────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                      EXECUTION BACKENDS                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Native     │  │    WSL2      │  │   Docker     │              │
│  │  (Windows)   │  │ (Kali Linux) │  │  (Kali img)  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────────────┤
│                    SQLite Database (aiosqlite)                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 The 10-Stage Pipeline

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

> **Critical Rule**: The LLM never directly executes shell commands. It produces structured plans that are validated and executed through the security pipeline.

---

## 📦 Requirements

### System Requirements
| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (64-bit) |
| **Python** | 3.12 or higher |
| **RAM** | 16 GB minimum (32 GB recommended for larger models) |
| **GPU** | NVIDIA GPU with 8+ GB VRAM (optional, for GPU-accelerated inference) |
| **Disk** | 10 GB free (for models and data) |

### Required Software
| Software | Purpose | Installation |
|----------|---------|-------------|
| **[Ollama](https://ollama.com)** | Local LLM inference | Download from [ollama.com](https://ollama.com/download) |
| **Python 3.12+** | Application runtime | [python.org](https://www.python.org/downloads/) |

### Optional Software (for full tool support)
| Software | Purpose | Installation |
|----------|---------|-------------|
| **WSL2 + Kali Linux** | Run security tools | `wsl --install -d kali-linux` |
| **Docker Desktop** | Containerized tool execution | [docker.com](https://www.docker.com/products/docker-desktop/) |

---

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/bidhansaha510-debug/aegiscyber-ai.git
cd aegiscyber-ai
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install and Start Ollama
```bash
# Download Ollama from https://ollama.com/download
# After installation, pull a model:
ollama pull llama3.1:latest

# For embeddings (optional):
ollama pull nomic-embed-text
```

### 5. (Optional) Set Up WSL2 with Kali Linux
```bash
# Install WSL2
wsl --install -d kali-linux

# Inside Kali, install tools:
sudo apt update && sudo apt install -y nmap nikto gobuster sqlmap amass subfinder nuclei
```

### 6. (Optional) Set Up Docker
```bash
# Pull the Kali Docker image
docker pull kalilinux/kali-rolling
```

---

## ⚡ Quick Start

### Launch the Desktop App
```bash
cd d:\Hacking_AI\aegiscyber-ai
python -m app.main
```

### Or Run the API Server
```bash
uvicorn app.api.server:app --host 127.0.0.1 --port 8741
```

### First Steps
1. **Configure Scope** — Click the 🎯 **Scope** button in the header and add your authorized targets (e.g., `192.168.1.0/24` or `example.com`)
2. **Go to Investigation tab** — Type a natural language request like:
   ```
   Scan 192.168.1.1 for open ports and identify running services
   ```
3. **Watch the AI Reasoning Panel** — See real-time pipeline progress on the right side
4. **Approve Commands** — If a medium/high risk command is generated, an approval dialog will appear
5. **View Results** — The AI analyzes tool output and provides a security assessment

---

## 📖 How to Use

### 🔍 Investigation Mode (AI Chat)

The Investigation tab is your main interaction point. Type natural language requests and the AI will:

1. **Plan** the investigation phases
2. **Select** the best tools
3. **Generate** commands
4. **Validate** against policy
5. **Execute** (with approval if needed)
6. **Parse** and **analyze** results
7. **Generate** a security report

**Example requests:**
```
Perform reconnaissance on target.local including DNS enumeration and port scanning

Find subdomains for example.com using passive techniques only

Scan 10.0.0.1 for web vulnerabilities on port 80 and 443

Enumerate SMB shares on 192.168.1.50

Analyze the SSL/TLS configuration of https://target.com
```

### 🖥️ Terminal Mode

The Terminal tab lets you run individual commands with policy validation:

1. Select the **backend** (native, wsl2, docker)
2. Type a command (e.g., `nmap -sV 192.168.1.1`)
3. The command goes through **policy validation** before execution
4. If the risk level requires approval, a dialog appears
5. Output streams to the terminal view

### 🔧 Tools Browser

The Tools tab shows all 25+ registered security tools with:
- **Installation status** — Whether the tool is found on each backend
- **Risk level** — SAFE, LOW, MEDIUM, HIGH classification
- **Capabilities** — What each tool can do
- **Search & filter** — Find tools by name, category, or capability

Click **🔄 Scan Tools** to auto-detect which tools are installed.

### 📋 Audit Logs

The Logs tab shows a real-time feed of all system events:
- Command executions
- Policy decisions
- Scope changes
- Kill switch events
- Errors and warnings

### ⚙️ Settings

Configure:
- **Ollama** — Host, model, temperature, max tokens
- **Security Policy** — Auto-approve thresholds, high-risk blocking
- **Execution** — WSL2/Docker toggle, default timeouts, concurrency limits

---

## 🔧 Tool Registry

Tools are defined in YAML files under `tool_registry/`. Each definition includes:

```yaml
name: nmap
description: Network exploration tool and security/port scanner
category:
  - PORT_SCANNING
  - SERVICE_ENUMERATION
  - NETWORK_RECON
binary: nmap
execution_backend:
  - wsl2
  - docker
  - native
capabilities:
  - port_scanning
  - service_detection
  - os_detection
  - script_scanning
arguments:
  - name: port_spec
    flag: "-p"
    description: Port specification
    arg_type: port_range
  - name: service_version
    flag: "-sV"
    description: Probe open ports for service/version info
    arg_type: boolean
danger_level: MEDIUM_RISK
parser: nmap
default_timeout: 300
```

### Adding a New Tool

1. Create a YAML file in `tool_registry/` (e.g., `mytool.yaml`)
2. Define the tool's name, binary, categories, capabilities, arguments, and risk level
3. (Optional) Add a parser in `app/parsers/` if the tool has structured output
4. Restart the application — the tool is automatically discovered

### Supported Categories
`PORT_SCANNING` · `SERVICE_ENUMERATION` · `NETWORK_RECON` · `WEB_RECON` · `DNS` · `SUBDOMAIN_DISCOVERY` · `VULNERABILITY_ASSESSMENT` · `OSINT` · `DOMAIN_OSINT` · `PACKET_ANALYSIS` · `PASSWORD_AUDITING` · `CTF` · `UTILITY`

---

## 🌐 OSINT Engine

The OSINT engine gathers intelligence from multiple sources and correlates findings in a knowledge graph.

### Connectors

| Connector | Source | Entity Types | API Key Required |
|-----------|--------|-------------|-----------------|
| **DNS** | Local DNS resolution | Domain, IP, Subdomain | No |
| **WHOIS** | WHOIS databases | Domain, IP | No |
| **crt.sh** | Certificate Transparency logs | Domain (subdomains) | No |
| **GitHub** | GitHub API | Organization, Username, Domain, Email | Optional |
| **URLScan.io** | urlscan.io API | Domain, URL, IP | Optional |
| **Shodan** | Shodan API | IP, Domain | Yes |

### Knowledge Graph

The OSINT engine builds a NetworkX-based knowledge graph tracking:

- **Entity Types**: Domain, IP, Subdomain, Email, Username, Organization, URL, Certificate, Technology, Service, Port, ASN, Hash
- **Relationship Types**: `resolves_to`, `has_subdomain`, `has_email`, `has_certificate`, `uses_technology`, `registered_by`, `hosted_on`, and more
- **Operations**: Entity search, relationship traversal, shortest path finding, subgraph extraction, statistical analysis

### Adding a New OSINT Connector

1. Create a new file in `app/osint/connectors/`
2. Extend `BaseOSINTConnector` and implement the `search()` method
3. Register it in `app/osint/engine.py`'s `_register_defaults()`

---

## 🛡️ Security & Safety

### Authorization Boundary

AegisCyber AI enforces a strict authorization model:

1. **Scope Definition** — Users must explicitly define authorized targets before any active operations
2. **Scope Types** — IP addresses, IP ranges (CIDR), domains, hostnames, URLs, wildcard domains
3. **Scope Validation** — Every command's target is checked against the scope before execution
4. **Localhost Exception** — `127.0.0.1`, `localhost`, and `::1` are always authorized

### Risk Classification

| Risk Level | Examples | Policy |
|-----------|---------|--------|
| 🟢 **SAFE** | `dig`, `whois`, `curl -I`, `ping` | Auto-approved |
| 🔵 **LOW_RISK** | `netcat`, `wget`, banner grabbing | Configurable auto-approve |
| 🟡 **MEDIUM_RISK** | `nmap`, `nikto`, `nuclei`, `gobuster` | Requires user approval |
| 🔴 **HIGH_RISK** | `sqlmap`, `hydra`, `metasploit`, `hashcat` | Requires approval (or blocked) |
| ⛔ **BLOCKED** | `rm`, `mkfs`, `dd`, `shutdown`, `reboot` | Always blocked |

### Dangerous Pattern Detection

The policy engine inspects command arguments for dangerous patterns:
- Exploit scripts (`--script=exploit`)
- Writing to system directories (`> /etc/`)
- Recursive deletion (`rm -rf`)
- Pipe-to-shell (`curl ... | sh`)
- SUID modifications (`chmod +s`)
- World-writable permissions (`chmod 777`)

### Kill Switch

The emergency stop button immediately:
- Terminates all running subprocesses
- Cancels all pending asyncio tasks
- Blocks new command execution
- Can be disengaged to resume operations

### Audit Trail

Every action is logged in JSONL format including:
- Timestamp, event type, user actions
- Command executions with full arguments
- Policy decisions with risk levels
- Scope changes and kill switch events

---

## 🔌 API Reference

When running the FastAPI server (`uvicorn app.api.server:app`), the following endpoints are available:

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health check (Ollama, backends, tools) |

### Chat & Investigation
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Process a cybersecurity research request through the full pipeline |
| `POST` | `/chat/simple` | Simple conversational chat without tool execution |

### Tools
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tools` | List all registered tools with installation status |
| `POST` | `/tools/scan` | Scan all backends for installed tools |

### Scope Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scope` | Get current target scope |
| `POST` | `/scope` | Set authorized target scope |

### OSINT
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/osint/search` | Run OSINT search across connectors |
| `GET` | `/osint/graph` | Get knowledge graph statistics |

### Kill Switch
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/kill-switch/engage` | Engage emergency stop |
| `POST` | `/kill-switch/disengage` | Disengage emergency stop |
| `GET` | `/kill-switch/status` | Check kill switch status |

### Example API Usage

```python
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8741")

# Set scope first
client.post("/scope", json={
    "entries": [
        {"scope_type": "ip_range", "value": "192.168.1.0/24"},
        {"scope_type": "domain", "value": "target.local"},
    ]
})

# Run an investigation
response = client.post("/chat", json={
    "message": "Scan 192.168.1.1 for open ports and services"
})
print(response.json()["response"])

# Run OSINT search
osint = client.post("/osint/search", json={
    "target_type": "domain",
    "target_value": "example.com",
    "connectors": ["dns", "crt", "whois"]
})
print(f"Found {osint.json()['entities_found']} entities")
```

---

## ⚙️ Configuration

Configuration is managed through environment variables (prefix: `AEGIS_`) or `app/config.py` defaults:

### Ollama
| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_OLLAMA__HOST` | `http://localhost:11434` | Ollama server URL |
| `AEGIS_OLLAMA__MODEL` | `llama3.1:latest` | Default inference model |
| `AEGIS_OLLAMA__TEMPERATURE` | `0.1` | Model temperature (lower = more deterministic) |
| `AEGIS_OLLAMA__MAX_TOKENS` | `4096` | Maximum generation tokens |
| `AEGIS_OLLAMA__EMBEDDING_MODEL` | `nomic-embed-text` | Model for embeddings |

### Security
| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_SECURITY__AUTO_APPROVE_SAFE` | `true` | Auto-approve SAFE commands |
| `AEGIS_SECURITY__AUTO_APPROVE_LOW_RISK` | `false` | Auto-approve LOW_RISK commands |
| `AEGIS_SECURITY__REQUIRE_APPROVAL_MEDIUM` | `true` | Require approval for MEDIUM_RISK |
| `AEGIS_SECURITY__REQUIRE_APPROVAL_HIGH` | `true` | Require approval for HIGH_RISK |
| `AEGIS_SECURITY__BLOCK_HIGH_RISK` | `false` | Block all HIGH_RISK commands |

### Execution
| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_EXECUTION__WSL_DISTRO` | `kali-linux` | WSL2 distribution name |
| `AEGIS_EXECUTION__DOCKER_IMAGE` | `kalilinux/kali-rolling` | Docker image for tool execution |
| `AEGIS_EXECUTION__MAX_CONCURRENT_EXECUTIONS` | `5` | Maximum simultaneous tool executions |
| `AEGIS_EXECUTION__DEFAULT_TIMEOUT` | `300` | Default command timeout in seconds |

---

## 📁 Project Structure

```
aegiscyber-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Application entry point
│   ├── config.py                        # Pydantic settings configuration
│   ├── logging_config.py                # Structured JSON logging
│   ├── ai/                              # AI reasoning pipeline (7 modules)
│   │   ├── ollama_client.py             # Async Ollama HTTP client
│   │   ├── planner.py                   # Task decomposition
│   │   ├── router.py                    # Tool selection & routing
│   │   ├── analyst.py                   # Result analysis
│   │   ├── verifier.py                  # Conclusion verification
│   │   ├── orchestrator.py              # Central pipeline coordinator
│   │   ├── memory.py                    # Conversation & investigation memory
│   │   └── prompts/                     # System prompts & templates
│   ├── api/                             # FastAPI REST server
│   │   └── server.py                    # 12 API endpoints
│   ├── database/                        # Persistence layer
│   │   ├── connection.py                # aiosqlite connection manager
│   │   └── migrations.py               # Schema migrations
│   ├── execution/                       # Command execution (6 modules)
│   │   ├── models.py                    # CommandPlan, ExecutionResult, PolicyDecision
│   │   ├── subprocess_backend.py        # Native Windows execution
│   │   ├── wsl_backend.py              # WSL2 execution
│   │   ├── docker_backend.py           # Docker execution
│   │   ├── sandbox.py                  # Concurrency & pattern validation
│   │   └── manager.py                  # Backend orchestration
│   ├── gui/                             # PySide6 desktop interface (8 modules)
│   │   ├── main_window.py              # Main application window
│   │   ├── theme.py                    # Dark cybersecurity theme
│   │   ├── dashboard.py               # Dashboard with stat cards
│   │   ├── terminal_view.py           # Terminal with policy validation
│   │   ├── tools_view.py             # Tool registry browser
│   │   ├── logs_view.py              # Audit log viewer
│   │   ├── settings_view.py          # Configuration UI
│   │   └── widgets/                   # 6 custom widgets
│   ├── osint/                           # OSINT intelligence (10 modules)
│   │   ├── models.py                   # Entity & relationship models
│   │   ├── engine.py                   # OSINT orchestration
│   │   ├── graph.py                    # NetworkX knowledge graph
│   │   ├── normalization.py           # Result normalization
│   │   └── connectors/                # 6 data source connectors
│   ├── parsers/                         # Output parsing (7 modules)
│   │   ├── nmap_parser.py             # Nmap XML/greppable/normal
│   │   ├── dns_parser.py             # dig/nslookup/host
│   │   ├── whois_parser.py           # WHOIS data
│   │   ├── http_parser.py            # HTTP headers/httpx
│   │   ├── generic_parser.py         # Auto-detect JSON/CSV/text
│   │   └── registry.py               # Parser dispatch
│   ├── security/                        # Security subsystem (4 modules)
│   │   ├── authorization.py           # Scope-based target authorization
│   │   ├── audit.py                   # JSONL audit logging
│   │   ├── kill_switch.py            # Emergency process termination
│   │   └── secrets.py                # Encrypted secrets vault
│   └── tools/                           # Tool management (5 modules)
│       ├── schemas.py                 # ToolDefinition, ToolScore models
│       ├── registry.py               # YAML-based tool registry
│       ├── discovery.py              # Automatic tool scanning
│       ├── policy.py                 # Risk classification engine
│       └── command_planner.py        # Scored tool selection
├── tool_registry/                       # 25 YAML tool definitions
│   ├── nmap.yaml
│   ├── dig.yaml
│   ├── whois.yaml
│   ├── curl.yaml
│   └── ... (21 more)
├── pyproject.toml                       # Build configuration
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

---

## 🔌 Extending AegisCyber

### Add a New Security Tool

Create `tool_registry/mytool.yaml`:
```yaml
name: mytool
description: My custom security tool
category: [WEB_RECON]
binary: mytool
execution_backend: [wsl2]
capabilities: [custom_scanning]
input_types: [url]
output_types: [vulnerabilities]
arguments:
  - name: target
    flag: "-t"
    arg_type: url
    required: true
danger_level: MEDIUM_RISK
parser: generic
default_timeout: 120
```

### Add a New Output Parser

Create `app/parsers/mytool_parser.py`:
```python
from app.parsers.base import BaseParser

class MyToolParser(BaseParser):
    PARSER_NAME = "mytool"
    SUPPORTED_TOOLS = ["mytool"]

    def parse(self, raw_output, tool_name="", command=""):
        # Parse the raw output into structured data
        return {"findings": [], "format": "mytool"}
```

Register it in `app/parsers/registry.py`.

### Add a New OSINT Connector

Create `app/osint/connectors/myconnector.py`:
```python
from app.osint.connectors.base import BaseOSINTConnector
from app.osint.models import OSINTResult, EntityType

class MyConnector(BaseOSINTConnector):
    CONNECTOR_NAME = "myconnector"
    SUPPORTED_ENTITIES = [EntityType.DOMAIN]

    async def search(self, entity_type, value, **kwargs):
        # Query your data source
        return [OSINTResult(
            source="myconnector",
            entity_type="domain",
            value=value,
            confidence=0.8,
        )]
```

Register it in `app/osint/engine.py`.

---

## ⚠️ Disclaimer

**AegisCyber AI is intended exclusively for:**
- ✅ Authorized penetration testing with explicit written permission
- ✅ CTF (Capture The Flag) competitions
- ✅ Cyber range and lab environments
- ✅ Security research on your own infrastructure
- ✅ Educational and training purposes

**It must NOT be used for:**
- ❌ Unauthorized access to systems
- ❌ Scanning or attacking systems without permission
- ❌ Any illegal or unethical activity

The developers assume no liability for misuse. Users are solely responsible for ensuring they have proper authorization before using any tools or features. Always follow applicable laws and regulations.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with 🔐 security-first principles**

[Report Bug](../../issues) · [Request Feature](../../issues) · [Documentation](../../wiki)

</div>
