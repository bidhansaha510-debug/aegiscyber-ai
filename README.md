<p align="center">
  <h1 align="center">🛡️ AegisCyber AI</h1>
  <p align="center">
    <strong>AI-Powered Autonomous Cybersecurity Research, Reconnaissance, OSINT & Security-Testing Assistant</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#installation">Installation</a> •
    <a href="#configuration">Configuration</a> •
    <a href="#usage">Usage</a> •
    <a href="#project-structure">Project Structure</a> •
    <a href="#license">License</a>
  </p>
</p>

---

AegisCyber AI is a locally-hosted, AI-driven offensive security platform that combines a local LLM (via [Ollama](https://ollama.com)) with **74+ security tools**, a PySide6 desktop GUI, stealth/OPSEC-aware execution, MITRE ATT&CK mapping, OSINT graph analysis, and autonomous exploit generation — all running on your own hardware with zero cloud dependencies.

> **⚠️ Ethical Use Disclaimer**
> This software is designed **exclusively** for authorized security testing, penetration testing engagements, CTF competitions, and cybersecurity research. Always obtain explicit written authorization before testing any target. Unauthorized use against systems you do not own or have permission to test is illegal and unethical.

---

## Features

### 🤖 AI Orchestration
- **Local LLM Integration** — Connects to Ollama for fully offline, private inference (default: `llama3`). Supports any Ollama-compatible model with configurable temperature, token limits, and a dedicated code-generation model slot.
- **Multi-Agent Pipeline** — Planner → Router → Executor → Analyst → Verifier chain with automatic task decomposition, tool selection, output parsing, and finding verification.
- **Self-Healing Execution** — When a command fails (bad syntax, missing binary, timeout), the orchestrator reads the error output, asks the LLM for a corrected command, and retries — including auto-installing missing tools via `apt` on the WSL2/Kali backend.
- **Conversational Memory** — Conversation history, per-investigation fact store, and tool performance memory for context-aware follow-up queries.

### 🔧 74+ Security Tools
A YAML-based tool registry with structured definitions for 74 tools covering:

| Category | Tools (examples) |
|---|---|
| **Port Scanning** | nmap, masscan, rustscan, naabu |
| **Web Recon** | nikto, gobuster, ffuf, feroxbuster, dirsearch, wfuzz, katana |
| **Subdomain Discovery** | subfinder, amass, assetfinder, massdns |
| **DNS** | dig, dnsrecon, dnsx, fierce |
| **Vulnerability Assessment** | nuclei, sqlmap, dalfox, xsstrike, commix, wapiti |
| **TLS/SSL Analysis** | sslscan, sslyze, testssl |
| **OSINT** | theharvester, spiderfoot, shodan, censys, uncover |
| **Network Enumeration** | enum4linux, netexec, smbclient, smbmap, ldapsearch, nbtscan, snmpwalk, onesixtyone |
| **Web Crawling** | gospider, hakrawler, gau, waybackurls, paramspider |
| **Password Auditing** | hydra, john, hashcat |
| **CMS Scanning** | wpscan, joomscan, droopescan |
| **Packet Analysis** | tshark, tcpdump, wireshark |
| **Exploitation** | metasploit, responder |
| **Utility** | curl, wget, whois, httpx, httprobe, arjun, wafw00f, whatweb, eyewitness, trufflehog, gitdorker |

Each tool definition includes capabilities, arguments with types, example commands, output parsing patterns, error patterns, risk levels, and default timeouts.

### 🕵️ Stealth / OPSEC Mode
- **OPSEC Engine** — Assigns a 0–100 detection-risk score to every command before execution, factoring in IDS/WAF signature databases, traffic volume profiles, log footprints, and EDR detection matrices (CrowdStrike, SentinelOne, Elastic SIEM, Splunk ES, Microsoft Defender).
- **Signature Evader** — Maintains a database of known IDS/WAF signatures per tool and auto-generates evasion flags (e.g., custom User-Agents, packet padding, timing adjustments).
- **Traffic Profiler** — Jitter injection, rate limiting, burst control, and business-hours awareness with configurable profiles: `paranoid`, `careful`, `normal`, `aggressive`.
- **LOLBin Engine** — Living-off-the-Land binary resolver with a YAML registry of native OS binaries (GTFOBins / LOLBAS). When stealth mode is active, high-OPSEC tools are automatically replaced with LOLBin equivalents.
- **Stealth Plan Transforms** — Reorders plan phases to prioritize passive techniques, inserts OPSEC cooldown delays between active operations, and downgrades risk levels.

### 🗺️ MITRE ATT&CK Integration
- **ATT&CK Mapper** — Automatically tags every tool execution with corresponding ATT&CK tactic/technique IDs and tracks kill-chain coverage across an investigation.
- **ATT&CK Navigator Export** — Generates JSON layers compatible with [MITRE ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/) for visualization of investigation coverage with color-coded technique scores.

### 🌐 OSINT Engine & Knowledge Graph
- **Multi-Connector Architecture** — Pluggable connectors for DNS, WHOIS, crt.sh (Certificate Transparency), GitHub, URLScan, and Shodan.
- **Knowledge Graph** — NetworkX-backed directed graph that correlates discovered entities (domains, IPs, emails, certificates, etc.) and their relationships across data sources.
- **Normalization & Deduplication** — Unified entity model with confidence scoring and automatic deduplication.

### ⚔️ Weapon Mode (Autonomous Offensive)
- Plans the complete kill chain including exploitation phases.
- Auto-approves every risk level (no interactive prompts).
- Generates working exploit code (POC scripts) for confirmed findings using the LLM, with AST validation, stdlib-only enforcement, and auto-repair.
- Saves exploit scripts to disk and optionally executes them through the configured backend.
- All operations remain bound by the authorized target scope and kill switch.

### 🖥️ Desktop GUI (PySide6)
- **Chat Interface** — Conversational interaction with the AI orchestrator with streaming responses.
- **Reasoning Panel** — Real-time visualization of the AI's multi-step reasoning chain (planning → routing → executing → analyzing).
- **Live Terminal** — Streams stdout/stderr from tool executions in real time.
- **Dashboard** — System status cards showing backend availability, tool counts, GPU info, and investigation metrics.
- **Tools Page** — Browse, search, and discover all 74+ registered tools with installation status.
- **Logs & Settings Pages** — View structured JSON logs and configure all system settings.
- **POC Viewer** — Renders generated Proof-of-Concept reports with embedded exploit code.
- **Scope Dialog** — Define and confirm authorized target scope (IPs, domains, ranges, URLs, wildcards).
- **Approval Dialog** — Interactive approval prompts for medium/high risk operations.
- **Sandbox Attack Window** — Dedicated window for autonomous offensive operations.
- **Kill Switch Button** — One-click emergency stop that immediately terminates all running processes and tasks.
- **Dark Theme** — Professional dark UI with custom color system, glassmorphism accents, and monospace terminal fonts.

### 🔒 Security & Safety
- **Authorization Manager** — Enforces target scoping with IP range, domain, hostname, URL, and wildcard matching. All operations validated against the confirmed scope.
- **Policy Engine** — Classifies commands into risk tiers (`SAFE` / `LOW_RISK` / `MEDIUM_RISK` / `HIGH_RISK` / `BLOCKED`) with configurable auto-approval, dangerous argument pattern detection, and executable blacklists.
- **Kill Switch** — Emergency stop mechanism that terminates all active processes and async tasks instantly.
- **Audit Logger** — Full audit trail of every action, command, policy decision, and finding — persisted to both JSONL files and the SQLite database.
- **Secrets Vault** — Fernet-encrypted local vault for API keys (Shodan, GitHub, Censys, etc.) with auto-generated key management.

### ⚙️ Execution Backends
- **WSL2** — Primary backend targeting Kali Linux on WSL2, with automatic distro detection.
- **Docker** — Container-based execution with `kalilinux/kali-rolling`.
- **Native (Subprocess)** — Direct local execution for OS-native tools.
- **Sandbox** — Concurrency limiting, output size caps, command validation, and timeout enforcement across all backends.
- **Auto-Installer** — Detects "command not found" errors and automatically installs missing tools via `apt` (80+ package mappings) or `go install` in the execution backend.

### 📡 REST API
- FastAPI-powered local API server (default port `8741`) with endpoints for:
  - Chat/investigation requests
  - Health checks and backend status
  - Scope management
  - Tool listing and discovery
  - OSINT searches
  - Kill switch control

### 📊 Structured Logging
- JSON-formatted structured logging (JSONL) with rotating file handlers.
- Separate error log for critical issues.
- Console output with human-readable formatting.

### 🗃️ Database
- SQLite (via aiosqlite) with migration system.
- Tables for investigations, tasks, executions, tool outputs, OSINT entities, findings, conversation memory, and investigation facts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PySide6 Desktop GUI                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌──────────┐  │
│  │   Chat   │ │Reasoning │ │ Terminal  │ │ POC  │ │Dashboard │  │
│  │  Widget  │ │  Panel   │ │   Live    │ │Viewer│ │  & Tabs  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬───┘ └──────────┘  │
│       │             │            │           │                   │
│       └─────────────┴────────────┴───────────┘                   │
│                          │ AsyncBridge                            │
├──────────────────────────┼───────────────────────────────────────┤
│                    Orchestrator                                   │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐  ┌─────────┐ │
│  │Planner │→ │ Router │→ │Executor│→ │ Analyst  │→ │Verifier │ │
│  │ (LLM)  │  │ (LLM)  │  │        │  │  (LLM)   │  │ (LLM)  │ │
│  └────────┘  └────────┘  └────┬───┘  └──────────┘  └─────────┘ │
│                               │                                  │
│  ┌────────────────────────────┼──────────────────────────────┐   │
│  │              Execution Manager                            │   │
│  │  ┌──────┐    ┌──────┐    ┌──────┐    ┌─────────┐         │   │
│  │  │ WSL2 │    │Docker│    │Native│    │ Sandbox │         │   │
│  │  │(Kali)│    │      │    │      │    │(limiter)│         │   │
│  │  └──────┘    └──────┘    └──────┘    └─────────┘         │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │  OPSEC   │ │Signature │ │ Traffic  │ │     LOLBin       │    │
│  │  Engine  │ │ Evader   │ │ Profiler │ │     Engine       │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │  MITRE   │ │  OSINT   │ │Knowledge │ │   POC Generator  │    │
│  │  Mapper  │ │  Engine  │ │  Graph   │ │ + Exploit Builder│    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
│                                                                  │
│  ┌────────┐ ┌──────────┐ ┌──────┐ ┌───────┐ ┌──────────────┐   │
│  │ Policy │ │  Audit   │ │ Kill │ │Secrets│ │Tool Registry │   │
│  │ Engine │ │  Logger  │ │Switch│ │ Vault │ │  (74 YAMLs)  │   │
│  └────────┘ └──────────┘ └──────┘ └───────┘ └──────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│  Ollama (Local LLM)  │  SQLite (aiosqlite)  │  FastAPI (REST)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Python** | ≥ 3.12 | Required |
| **Ollama** | Latest | Local LLM inference server |
| **WSL2 + Kali Linux** | Latest | Primary execution backend (recommended) |
| **Docker** | Latest | Optional alternative backend |
| **GPU** | CUDA-capable | Optional, for accelerated inference & model fine-tuning |

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/aegiscyber-ai.git
   cd aegiscyber-ai
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   # Or with dev dependencies:
   pip install -e ".[dev]"
   ```

4. **Install and start Ollama**
   ```bash
   # Download from https://ollama.com
   ollama pull llama3
   # Optional: dedicated codegen model
   ollama pull qwen2.5-coder:7b
   ```

5. **Set up WSL2 with Kali Linux** (recommended)
   ```bash
   wsl --install -d kali-linux
   ```

6. **Install security tools in Kali**
   ```bash
   wsl -d kali-linux -- bash scripts/install_all_tools.sh
   ```

7. **Launch AegisCyber AI**
   ```bash
   aegiscyber
   # Or directly:
   python -m app.main
   ```

---

## Configuration

AegisCyber AI is configured via environment variables (prefixed `AEGIS_`) or by modifying the `AppConfig` defaults in `app/config.py`. Nested settings use `__` as delimiter.

### Key Configuration Sections

| Section | Env Prefix | Description |
|---|---|---|
| `ollama` | `AEGIS_OLLAMA__` | LLM host, model, codegen model, timeout, temperature, max tokens |
| `execution` | `AEGIS_EXECUTION__` | Timeouts, concurrency, WSL distro, Docker image, backend toggles |
| `security` | `AEGIS_SECURITY__` | Scope confirmation, auto-approval rules, allowed networks, blocked executables |
| `stealth` | `AEGIS_STEALTH__` | OPSEC threshold, traffic profile, jitter, rate limits, evasion flags |
| `selfheal` | `AEGIS_SELFHEAL__` | Auto-retry count, auto-install toggle, install timeout |
| `weapon` | `AEGIS_WEAPON__` | Weapon mode toggle, auto-approve all, exploit execution, reverse shell handlers |
| `model` | `AEGIS_MODEL__` | Specialized model path, embedding dimensions, GPU device, LoRA parameters |
| `database` | `AEGIS_DATABASE__` | SQLite database path |
| `api` | `AEGIS_API__` | REST API host, port, API key |

### Example Environment Variables

```bash
# Use a different Ollama model
export AEGIS_OLLAMA__MODEL=mistral:latest

# Set a dedicated code generation model
export AEGIS_OLLAMA__CODEGEN_MODEL=qwen2.5-coder:7b

# Change the WSL distro
export AEGIS_EXECUTION__WSL_DISTRO=kali-linux

# Enable debug logging
export AEGIS_DEBUG=true

# Enable stealth mode by default
export AEGIS_STEALTH__STEALTH_MODE_DEFAULT=true
```

### Secrets Management

API keys for OSINT connectors (Shodan, GitHub, Censys, URLScan) are stored in a Fernet-encrypted local vault at `data/secrets/vault.enc`. Manage them through the GUI Settings page or programmatically via `SecretsManager`.

---

## Usage

### Desktop GUI

Launch with `aegiscyber` or `python -m app.main`. The main window includes:

1. **Define Scope** — Click the scope button to add authorized targets (IPs, domains, CIDR ranges, URLs).
2. **Chat** — Type natural-language requests like:
   - *"Scan example.com for open ports and services"*
   - *"Find subdomains of example.com and check which are alive"*
   - *"Run a full vulnerability assessment on 192.168.1.0/24"*
   - *"Do OSINT on example.com — DNS, WHOIS, certificate transparency"*
3. **Watch** — The Reasoning Panel shows the AI's plan → tool selection → execution → analysis chain in real time. The Live Terminal streams raw tool output.
4. **Review** — Findings, POC reports, and exploit scripts are displayed in the POC Viewer.
5. **Emergency Stop** — Hit the Kill Switch button at any time to terminate all operations.

### Stealth Mode

Toggle stealth mode from the GUI or configuration to enable:
- OPSEC-scored tool selection
- Automatic evasion flag injection
- Jitter delays between operations
- LOLBin substitutions for high-noise tools
- Business-hours awareness

### Weapon Mode

Enable weapon mode for fully autonomous offensive operations:
- Complete kill-chain planning including exploitation
- Auto-generated, validated exploit scripts
- Automatic exploit execution with verification
- All operations remain scope-bound with kill switch override

### REST API

When enabled (default), the API server runs at `http://127.0.0.1:8741`:

```bash
# Health check
curl http://localhost:8741/health

# Send a chat request
curl -X POST http://localhost:8741/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Scan example.com for open ports"}'

# List available tools
curl http://localhost:8741/tools

# Run an OSINT search
curl -X POST http://localhost:8741/osint/search \
  -H "Content-Type: application/json" \
  -d '{"target_type": "domain", "target_value": "example.com"}'
```

---

## Project Structure

```
aegiscyber-ai/
├── app/
│   ├── main.py                    # Application entry point & system initialization
│   ├── config.py                  # Pydantic-based configuration (all settings)
│   ├── logging_config.py          # Structured JSON logging setup
│   │
│   ├── ai/                        # AI / LLM layer
│   │   ├── orchestrator.py        # Core orchestration engine (1094 lines)
│   │   ├── ollama_client.py       # Ollama HTTP client (generate, chat, embeddings, stream)
│   │   ├── planner.py             # Task decomposition into phased plans
│   │   ├── router.py              # Tool selection & command planning
│   │   ├── analyst.py             # LLM-based output analysis
│   │   ├── verifier.py            # Finding verification
│   │   ├── memory.py              # Conversation, investigation & tool memory
│   │   ├── poc_generator.py       # POC report & exploit script generation
│   │   ├── exploit_builder.py     # Code extraction, validation, AST repair
│   │   ├── json_utils.py          # Robust JSON extraction & LLM-assisted repair
│   │   └── prompts/               # System prompts & task templates
│   │       ├── system_prompts.py
│   │       └── task_templates.py
│   │
│   ├── execution/                 # Command execution layer
│   │   ├── manager.py             # Execution orchestration & backend dispatch
│   │   ├── models.py              # CommandPlan, ExecutionRequest/Result, PolicyDecision
│   │   ├── wsl_backend.py         # WSL2/Kali execution backend
│   │   ├── docker_backend.py      # Docker container execution backend
│   │   ├── subprocess_backend.py  # Native subprocess backend
│   │   ├── sandbox.py             # Concurrency, timeout & output size enforcement
│   │   └── hardware.py            # GPU detection & system info
│   │
│   ├── tools/                     # Tool management
│   │   ├── registry.py            # YAML-based tool definition loader
│   │   ├── schemas.py             # ToolDefinition, ToolArgument, ToolScore models
│   │   ├── discovery.py           # Runtime tool availability detection
│   │   ├── policy.py              # Risk classification & execution policy
│   │   ├── command_planner.py     # Tool scoring & command plan generation
│   │   └── auto_installer.py      # Automatic missing-tool installation
│   │
│   ├── parsers/                   # Tool output parsers
│   │   ├── registry.py            # Parser dispatch registry
│   │   ├── base.py                # Base parser interface
│   │   ├── nmap_parser.py         # Nmap output parser
│   │   ├── dns_parser.py          # DNS tool output parser
│   │   ├── http_parser.py         # HTTP tool output parser
│   │   ├── whois_parser.py        # WHOIS output parser
│   │   └── generic_parser.py      # Fallback generic parser
│   │
│   ├── osint/                     # OSINT engine
│   │   ├── engine.py              # Multi-connector OSINT orchestration
│   │   ├── graph.py               # NetworkX knowledge graph
│   │   ├── models.py              # Entity, Relationship, Search models
│   │   ├── normalization.py       # Entity normalization & deduplication
│   │   └── connectors/            # Pluggable data source connectors
│   │       ├── base.py
│   │       ├── dns_connector.py
│   │       ├── whois_connector.py
│   │       ├── crt_connector.py
│   │       ├── github_connector.py
│   │       ├── shodan_connector.py
│   │       └── urlscan_connector.py
│   │
│   ├── stealth/                   # OPSEC & evasion layer
│   │   ├── opsec_engine.py        # Detection-risk scoring & stealth fallbacks
│   │   ├── signature_evader.py    # IDS/WAF signature database & evasion flags
│   │   └── traffic_profiler.py    # Jitter, rate limiting & timing profiles
│   │
│   ├── lolbin/                    # Living-off-the-Land binaries
│   │   ├── lolbin_engine.py       # LOLBin resolver & technique mapper
│   │   └── lolbin_registry.yaml   # Registry of native OS binaries
│   │
│   ├── mitre/                     # MITRE ATT&CK integration
│   │   ├── attack_mapper.py       # Tool → technique mapping & coverage tracking
│   │   └── attack_navigator.py    # ATT&CK Navigator layer JSON export
│   │
│   ├── security/                  # Security controls
│   │   ├── authorization.py       # Target scope management & validation
│   │   ├── audit.py               # Audit event logging (JSONL + SQLite)
│   │   ├── kill_switch.py         # Emergency stop — terminates all processes
│   │   └── secrets.py             # Fernet-encrypted API key vault
│   │
│   ├── database/                  # Persistence
│   │   ├── connection.py          # Async SQLite connection manager
│   │   └── migrations.py          # Schema versioning & migration runner
│   │
│   ├── gui/                       # PySide6 desktop interface
│   │   ├── main_window.py         # Main application window & AsyncBridge
│   │   ├── theme.py               # Color system, fonts & global stylesheet
│   │   ├── dashboard.py           # Dashboard page with stat cards
│   │   ├── terminal_view.py       # Terminal history page
│   │   ├── tools_view.py          # Tool browser & discovery page
│   │   ├── logs_view.py           # Log viewer page
│   │   ├── settings_view.py       # Settings configuration page
│   │   └── widgets/               # Reusable UI components
│   │       ├── chat_widget.py     # Chat input/output widget
│   │       ├── reasoning_panel.py # AI reasoning step visualization
│   │       ├── live_terminal.py   # Live stdout/stderr streaming
│   │       ├── status_bar.py      # Bottom status bar
│   │       ├── kill_switch.py     # Emergency stop button
│   │       ├── scope_dialog.py    # Target scope configuration dialog
│   │       ├── approval_dialog.py # Risk approval dialog
│   │       ├── sandbox_window.py  # Autonomous attack window
│   │       └── poc_viewer.py      # POC report & exploit code viewer
│   │
│   ├── api/                       # REST API
│   │   └── server.py              # FastAPI endpoints
│   │
│   ├── c2/                        # Command & Control (reserved)
│   └── research/                  # Research module (reserved)
│
├── tool_registry/                 # 74 YAML tool definitions
│   ├── nmap.yaml
│   ├── subfinder.yaml
│   ├── nuclei.yaml
│   ├── ... (74 files)
│   └── xsstrike.yaml
│
├── scripts/
│   ├── install_all_tools.sh       # Bulk tool installer for Kali/WSL2
│   ├── install_go_tools.sh        # Go-based tool installer
│   ├── generate_tool_yamls.py     # Tool definition generator
│   ├── test_graph.py              # Knowledge graph test script
│   └── test_parser.py             # Parser test script
│
├── configs/                       # External configuration files (user-managed)
├── data/                          # Runtime data (gitignored)
│   ├── aegiscyber.db              # SQLite database
│   └── secrets/                   # Encrypted API key vault
├── logs/                          # Application logs (gitignored)
│   ├── aegiscyber.jsonl           # Main structured log
│   ├── audit.jsonl                # Security audit trail
│   └── errors.jsonl               # Error-only log
├── exploits/                      # Generated exploit scripts (gitignored)
│
├── pyproject.toml                 # Project metadata & dependencies
├── requirements.txt               # Pip requirements
├── LICENSE                        # MIT License
└── .gitignore
```

---

## Adding a New Tool

Create a YAML file in `tool_registry/` following the schema:

```yaml
name: mytool
description: What the tool does
category:
  - NETWORK_RECON          # From ToolCategory enum
binary: mytool
execution_backend:
  - wsl2
capabilities:
  - port_scanning
  - host_discovery
input_types:
  - ip_address
  - domain
output_types:
  - open_ports
arguments:
  - name: verbose
    flag: "-v"
    description: Enable verbose output
    arg_type: boolean
    required: false
examples:
  - description: Basic scan
    command: "mytool -v {target}"
    expected_output: Scan results
    risk_level: LOW_RISK
expected_output_patterns:
  - name: result_line
    pattern: 'FOUND: (.+)'
    description: Matches result lines
parser: generic
danger_level: LOW_RISK
default_timeout: 120
```

The tool will be automatically loaded on the next launch.

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check .

# Run tests
pytest

# Run with debug logging
AEGIS_DEBUG=true python -m app.main
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12+ |
| **GUI** | PySide6 (Qt 6) |
| **LLM** | Ollama (local) — llama3, qwen2.5-coder, etc. |
| **API** | FastAPI + Uvicorn |
| **Database** | SQLite via aiosqlite |
| **ML/Embeddings** | PyTorch, Transformers, Sentence-Transformers, PEFT (LoRA) |
| **Graph** | NetworkX |
| **Config** | Pydantic + Pydantic-Settings |
| **Crypto** | cryptography (Fernet) |
| **Logging** | orjson-based structured JSONL |
| **HTTP** | aiohttp, httpx |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 AegisCyber AI Team
