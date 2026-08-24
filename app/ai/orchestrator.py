from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.planner import Planner, TaskPlan, TaskPhase
from app.ai.router import CyberTaskRouter, RoutingResult
from app.ai.analyst import Analyst
from app.ai.verifier import Verifier
from app.ai.memory import MemoryManager
from app.ai.prompts.system_prompts import ORCHESTRATOR_SYSTEM
from app.ai.prompts.task_templates import FINAL_REPORT_TEMPLATE
from app.execution.manager import ExecutionManager
from app.execution.models import CommandPlan, ExecutionRequest, ExecutionResult, ExecutionStatus, PolicyDecision
from app.tools.registry import ToolRegistry
from app.tools.policy import PolicyEngine
from app.tools.command_planner import CommandPlanner
from app.parsers.registry import ParserRegistry
from app.osint.engine import OSINTEngine
from app.osint.models import OSINTSearchRequest, EntityType
from app.security.authorization import AuthorizationManager
from app.security.audit import AuditLogger
from app.security.kill_switch import KillSwitch
from app.logging_config import get_logger

logger = get_logger("ai.orchestrator")


class ReasoningStep(BaseModel):
    step: str
    status: str = "pending"
    detail: str = ""


class OrchestratorState(BaseModel):
    investigation_id: str = ""
    current_phase: str = ""
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list)
    is_running: bool = False
    error: str = ""


class Orchestrator:
    def __init__(
        self,
        ollama_client: OllamaClient,
        execution_manager: ExecutionManager,
        tool_registry: ToolRegistry,
        policy_engine: PolicyEngine,
        parser_registry: ParserRegistry,
        osint_engine: OSINTEngine,
        auth_manager: AuthorizationManager,
        audit_logger: AuditLogger,
        kill_switch: KillSwitch,
    ) -> None:
        self._ollama = ollama_client
        self._exec_manager = execution_manager
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine
        self._parser_registry = parser_registry
        self._osint_engine = osint_engine
        self._auth_manager = auth_manager
        self._audit = audit_logger
        self._kill_switch = kill_switch

        self._command_planner = CommandPlanner(tool_registry)
        self._planner = Planner(ollama_client)
        self._router = CyberTaskRouter(ollama_client, tool_registry, self._command_planner)
        self._analyst = Analyst(ollama_client)
        self._verifier = Verifier(ollama_client)
        self._memory = MemoryManager()

        self._state = OrchestratorState()
        self._on_reasoning_update: list[Callable[[OrchestratorState], None]] = []
        self._on_approval_required: Callable[[CommandPlan, PolicyDecision], bool] | None = None
        self._approval_response: bool | None = None

    @property
    def state(self) -> OrchestratorState:
        return self._state

    def on_reasoning_update(self, callback: Callable[[OrchestratorState], None]) -> None:
        self._on_reasoning_update.append(callback)

    def set_approval_handler(self, handler: Callable[[CommandPlan, PolicyDecision], bool]) -> None:
        self._on_approval_required = handler

    def submit_approval_decision(self, approved: bool) -> None:
        self._approval_response = approved

    async def process_request(self, user_request: str, investigation_id: str = "") -> str:
        if self._kill_switch.is_engaged:
            return "Execution blocked: Emergency stop (Kill Switch) is currently engaged."

        investigation_id = investigation_id or str(uuid.uuid4())[:8]
        self._state = OrchestratorState(
            investigation_id=investigation_id,
            is_running=True,
        )

        inv_memory = self._memory.get_investigation(investigation_id)
        self._memory.conversation.add_message("user", user_request)

        try:
            self._update_reasoning("UNDERSTANDING REQUEST", "active", "Analyzing user intent")

            scope_info = self._format_scope()
            available_backends = ", ".join(self._exec_manager.get_available_backends())
            available_tools = ", ".join(
                t.name for t in self._tool_registry.get_all_tools()
                if self._tool_registry.is_installed(t.name)
            )

            plan = await self._planner.decompose(
                user_request=user_request,
                scope_info=scope_info,
                available_backends=available_backends,
                available_tools=available_tools,
            )

            self._update_reasoning("UNDERSTANDING REQUEST", "complete", f"Intent: {plan.intent}")
            self._update_reasoning("TASK PLAN", "active", f"{len(plan.phases)} phases planned")

            all_findings: list[dict[str, Any]] = []
            blocked_reasons: list[str] = []

            for phase in plan.phases:
                if self._kill_switch.is_engaged:
                    break

                self._state.current_phase = phase.name
                self._update_reasoning(f"PHASE {phase.phase_number}: {phase.name}", "active", phase.description)

                routing = await self._router.route(
                    phase_name=phase.name,
                    phase_description=phase.description,
                    category=phase.category,
                    required_capabilities=phase.required_capabilities,
                    target=plan.target,
                    risk_limit=phase.risk_level,
                )

                for tool_selection in routing.selected_tools:
                    if self._kill_switch.is_engaged:
                        break
                    if not tool_selection.command_plan:
                        continue

                    self._update_reasoning(f"TOOL: {tool_selection.tool_name}", "active", "Validating command")

                    tool_def = self._tool_registry.get_tool(tool_selection.tool_name)
                    policy = self._policy_engine.evaluate(
                        tool_selection.command_plan,
                        tool_def,
                        investigation_id,
                    )

                    if not policy.allowed:
                        self._audit.log_policy_block(
                            tool_selection.tool_name,
                            tool_selection.command_plan.to_command_string(),
                            policy.reason,
                            policy.risk,
                        )
                        blocked_reasons.append(policy.reason)
                        self._update_reasoning(f"TOOL: {tool_selection.tool_name}", "blocked", policy.reason)
                        continue

                    if policy.requires_approval:
                        self._update_reasoning(
                            f"TOOL: {tool_selection.tool_name}",
                            "awaiting_approval",
                            f"Risk: {policy.risk} - Requires approval",
                        )
                        approved = await self._request_approval(tool_selection.command_plan, policy)
                        if not approved:
                            self._update_reasoning(f"TOOL: {tool_selection.tool_name}", "skipped", "User declined")
                            continue

                    self._update_reasoning(f"TOOL: {tool_selection.tool_name}", "running", "Executing command")
                    self._audit.log_command_execution(
                        task_id=investigation_id,
                        execution_id="",
                        tool_name=tool_selection.tool_name,
                        target=plan.target,
                        command=tool_selection.command_plan.to_command_string(),
                        policy_decision=policy.risk,
                        risk_level=policy.risk,
                    )

                    exec_request = ExecutionRequest(
                        task_id=investigation_id,
                        command_plan=tool_selection.command_plan,
                    )
                    exec_result = await self._exec_manager.execute(exec_request)

                    self._memory.tool_memory.record_execution(
                        tool_selection.tool_name,
                        exec_result.status == ExecutionStatus.COMPLETED,
                        exec_result.duration_seconds,
                        plan.target,
                    )

                    if exec_result.status == ExecutionStatus.COMPLETED:
                        self._update_reasoning(
                            f"TOOL: {tool_selection.tool_name}",
                            "complete",
                            f"Completed in {exec_result.duration_seconds:.1f}s",
                        )

                        parsed = self._parser_registry.parse_output(
                            exec_result.stdout,
                            tool_selection.tool_name,
                            tool_selection.command_plan.to_command_string(),
                        )
                        exec_result.parsed_output = parsed

                        analysis = await self._analyst.analyze(
                            tool_name=tool_selection.tool_name,
                            command=tool_selection.command_plan.to_command_string(),
                            structured_results=parsed,
                            raw_output=exec_result.stdout,
                            target=plan.target,
                            investigation_context=plan.intent,
                            known_facts=inv_memory.get_facts_summary(),
                        )

                        inv_memory.add_finding(tool_selection.tool_name, {
                            "parsed": parsed,
                            "analysis": analysis,
                        })

                        all_findings.append({
                            "tool": tool_selection.tool_name,
                            "parsed": parsed,
                            "analysis": analysis,
                        })
                    else:
                        error_msg = exec_result.error_message or exec_result.stderr
                        self._update_reasoning(f"TOOL: {tool_selection.tool_name}", "failed", error_msg[:200])

                phase.status = "complete"
                self._update_reasoning(f"PHASE {phase.phase_number}: {phase.name}", "complete", "Phase finished")

            self._update_reasoning("GENERATING REPORT", "active", "Synthesizing findings")

            if all_findings:
                final_report = await self._analyst.summarize_findings(all_findings, plan.target)
            elif blocked_reasons:
                target_str = plan.target or "the specified target"
                unique_reasons = "\n".join(f"- {r}" for r in set(blocked_reasons))
                final_report = (
                    f"**Execution Blocked by Policy Engine**\n\n"
                    f"Operations on `{target_str}` could not proceed due to security authorization boundaries:\n"
                    f"{unique_reasons}\n\n"
                    f"**How to authorize this target:**\n"
                    f"1. Click the **Scope** button at the top-right of the window.\n"
                    f"2. Add `{target_str}` as an authorized target (Domain, IP, or IP range).\n"
                    f"3. Click **Confirm Scope** and re-submit your security testing request."
                )
            else:
                final_report = await self._ollama.chat(
                    messages=self._memory.conversation.get_chat_messages() + [
                        {"role": "user", "content": user_request}
                    ],
                )
                if not final_report:
                    final_report = "I was unable to generate results for this request. Please check the tool availability and scope configuration."

            self._update_reasoning("GENERATING REPORT", "complete", "Report ready")
            self._memory.conversation.add_message("assistant", final_report)
            self._state.is_running = False
            return final_report

        except Exception as e:
            logger.error("Orchestrator error: %s", e, exc_info=True)
            self._state.is_running = False
            self._state.error = str(e)
            error_response = f"An error occurred during processing: {str(e)}"
            self._memory.conversation.add_message("assistant", error_response)
            return error_response

    async def chat(self, message: str) -> str:
        self._memory.conversation.add_message("user", message)

        messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM}
        ] + self._memory.conversation.get_chat_messages()

        response = await self._ollama.chat(messages=messages)
        if not response:
            response = "I'm unable to respond right now. Please check that Ollama is running."

        self._memory.conversation.add_message("assistant", response)
        return response

    async def _request_approval(self, command_plan: CommandPlan, policy: PolicyDecision) -> bool:
        if self._on_approval_required:
            self._approval_response = None
            self._on_approval_required(command_plan, policy)
            import asyncio
            for _ in range(600):
                if self._approval_response is not None:
                    return self._approval_response
                await asyncio.sleep(0.1)
            return False
        return False

    def _format_scope(self) -> str:
        scope = self._auth_manager.current_scope
        if not scope.entries:
            return "No scope defined"
        lines = []
        for entry in scope.entries:
            lines.append(f"{entry.scope_type.value}: {entry.value}")
        return "\n".join(lines)

    def _update_reasoning(self, step: str, status: str, detail: str) -> None:
        existing = None
        for rs in self._state.reasoning_steps:
            if rs.step == step:
                existing = rs
                break

        if existing:
            existing.status = status
            existing.detail = detail
        else:
            self._state.reasoning_steps.append(ReasoningStep(
                step=step, status=status, detail=detail,
            ))

        for callback in self._on_reasoning_update:
            try:
                callback(self._state)
            except Exception as e:
                logger.error("Reasoning update callback error: %s", e)
