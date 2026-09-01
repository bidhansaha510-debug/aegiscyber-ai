from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_config
from app.logging_config import setup_logging, get_logger

logger = get_logger("api.server")


app = FastAPI(
    title="AegisCyber AI API",
    version="1.0.0",
    description="Local AI-powered cybersecurity research assistant API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_components: dict[str, Any] = {}


def get_orchestrator():
    orch = _components.get("orchestrator")
    if not orch:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orch


class ChatRequest(BaseModel):
    message: str
    investigation_id: str = ""


class ChatResponse(BaseModel):
    response: str
    investigation_id: str = ""
    reasoning_steps: list[dict] = Field(default_factory=list)


class ScopeEntry(BaseModel):
    scope_type: str
    value: str


class ScopeRequest(BaseModel):
    entries: list[ScopeEntry]


class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool = False
    backends: dict[str, bool] = Field(default_factory=dict)
    tools_loaded: int = 0
    tools_installed: int = 0


class ToolsResponse(BaseModel):
    tools: list[dict] = Field(default_factory=list)
    total: int = 0
    installed: int = 0


class OSINTRequest(BaseModel):
    target_type: str
    target_value: str
    connectors: list[str] = Field(default_factory=list)


class OSINTResponse(BaseModel):
    entities_found: int = 0
    relationships_found: int = 0
    results: list[dict] = Field(default_factory=list)
    duration_seconds: float = 0.0


@app.get("/health", response_model=HealthResponse)
async def health_check():
    orchestrator = _components.get("orchestrator")
    ollama = _components.get("ollama_client")
    registry = _components.get("tool_registry")

    ollama_ok = False
    if ollama:
        ollama_ok = await ollama.health_check()

    backends = {}
    exec_mgr = _components.get("exec_manager")
    if exec_mgr:
        for name in exec_mgr.get_available_backends():
            backends[name] = True

    return HealthResponse(
        status="ok" if orchestrator else "degraded",
        ollama_connected=ollama_ok,
        backends=backends,
        tools_loaded=registry.get_tool_count() if registry else 0,
        tools_installed=registry.get_installed_count() if registry else 0,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    orchestrator = get_orchestrator()
    response = await orchestrator.process_request(request.message)
    return ChatResponse(
        response=response,
        investigation_id=orchestrator.state.investigation_id,
        reasoning_steps=[
            {"step": s.step, "status": s.status, "detail": s.detail}
            for s in orchestrator.state.reasoning_steps
        ],
    )


@app.post("/chat/simple")
async def chat_simple(request: ChatRequest):
    orchestrator = get_orchestrator()
    response = await orchestrator.chat(request.message)
    return {"response": response}


@app.get("/tools", response_model=ToolsResponse)
async def list_tools():
    registry = _components.get("tool_registry")
    if not registry:
        raise HTTPException(status_code=503, detail="Tool registry not initialized")

    tools = []
    for tool in registry.get_all_tools():
        tools.append({
            "name": tool.name,
            "description": tool.description,
            "categories": tool.category,
            "backends": tool.execution_backend,
            "risk_level": tool.danger_level,
            "installed": registry.is_installed(tool.name),
            "capabilities": tool.capabilities,
        })

    return ToolsResponse(
        tools=tools,
        total=registry.get_tool_count(),
        installed=registry.get_installed_count(),
    )


@app.post("/tools/scan")
async def scan_tools():
    discovery = _components.get("tool_discovery")
    if not discovery:
        raise HTTPException(status_code=503, detail="Tool discovery not initialized")
    results = await discovery.scan_all_tools()
    return {"results": results, "summary": discovery.get_discovery_summary()}


@app.post("/scope", response_model=dict)
async def set_scope(request: ScopeRequest):
    auth = _components.get("auth_manager")
    if not auth:
        raise HTTPException(status_code=503, detail="Authorization manager not initialized")

    from app.security.authorization import ScopeEntry as SE, ScopeType, TargetScope, AuthorizationState
    entries = []
    for entry in request.entries:
        entries.append(SE(scope_type=ScopeType(entry.scope_type), value=entry.value))
    target_scope = TargetScope(entries=entries, state=AuthorizationState.USER_CONFIRMED)
    auth.set_scope(target_scope)
    return {"status": "scope_updated", "entries": len(entries)}


@app.get("/scope")
async def get_scope():
    auth = _components.get("auth_manager")
    if not auth:
        raise HTTPException(status_code=503, detail="Authorization manager not initialized")
    scope = auth.current_scope
    return {
        "entries": [
            {"type": e.scope_type.value, "value": e.value}
            for e in scope.entries
        ]
    }


@app.post("/osint/search", response_model=OSINTResponse)
async def osint_search(request: OSINTRequest):
    osint = _components.get("osint_engine")
    if not osint:
        raise HTTPException(status_code=503, detail="OSINT engine not initialized")

    from app.osint.models import OSINTSearchRequest, EntityType
    search_request = OSINTSearchRequest(
        target_type=EntityType(request.target_type),
        target_value=request.target_value,
        connectors=request.connectors,
    )
    result = await osint.search(search_request)
    return OSINTResponse(
        entities_found=result.entities_found,
        relationships_found=result.relationships_found,
        results=[r.model_dump() for r in result.results],
        duration_seconds=result.duration_seconds,
    )


@app.get("/osint/graph")
async def get_osint_graph():
    osint = _components.get("osint_engine")
    if not osint:
        raise HTTPException(status_code=503, detail="OSINT engine not initialized")
    return osint.graph.get_statistics()


@app.post("/weapon/arm")
async def arm_weapon_mode():
    orchestrator = get_orchestrator()
    orchestrator.weapon_mode = True
    return {"status": "armed", "weapon_mode": True}


@app.post("/weapon/disarm")
async def disarm_weapon_mode():
    orchestrator = get_orchestrator()
    orchestrator.weapon_mode = False
    return {"status": "disarmed", "weapon_mode": False}


@app.get("/weapon/status")
async def weapon_status():
    orchestrator = get_orchestrator()
    config = get_config()
    pocs = orchestrator.poc_generator.get_all_pocs()
    return {
        "weapon_mode": orchestrator.weapon_mode,
        "execute_exploits": config.weapon.execute_exploits,
        "exploit_dir": config.weapon.exploit_dir,
        "poc_count": len(pocs),
        "exploit_count": sum(1 for p in pocs if p.exploit_file),
        "exploitation_successes": sum(1 for p in pocs if p.exploitation_success),
        "exploits": [
            {
                "title": p.title,
                "severity": p.severity,
                "target": p.target,
                "language": p.language,
                "exploit_file": p.exploit_file,
                "exploitation_success": p.exploitation_success,
            }
            for p in pocs
        ],
    }


@app.get("/weapon/report")
async def weapon_report():
    orchestrator = get_orchestrator()
    return {
        "markdown": orchestrator.poc_generator.export_pocs_markdown(),
    }


@app.post("/kill-switch/engage")
async def engage_kill_switch():
    ks = _components.get("kill_switch")
    if not ks:
        raise HTTPException(status_code=503, detail="Kill switch not initialized")
    ks.engage("API request")
    return {"status": "engaged"}


@app.post("/kill-switch/disengage")
async def disengage_kill_switch():
    ks = _components.get("kill_switch")
    if not ks:
        raise HTTPException(status_code=503, detail="Kill switch not initialized")
    ks.disengage()
    return {"status": "disengaged"}


@app.get("/kill-switch/status")
async def kill_switch_status():
    ks = _components.get("kill_switch")
    if not ks:
        raise HTTPException(status_code=503, detail="Kill switch not initialized")
    return {"engaged": ks.is_engaged}


def set_components(components: dict[str, Any]) -> None:
    global _components
    _components = components


def create_api_app(components: dict[str, Any]) -> FastAPI:
    set_components(components)
    return app
