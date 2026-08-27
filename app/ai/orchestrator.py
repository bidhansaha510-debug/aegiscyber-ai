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
from app.ai.poc_generator import POCGenerator
from app.stealth.opsec_engine import OPSECEngine
from app.stealth.traffic_profiler import TrafficProfiler
from app.stealth.signature_evader import SignatureEvader
from app.lolbin.lolbin_engine import LOLBinEngine
from app.mitre.attack_mapper import ATTACKMapper
from app.mitre.attack_navigator import ATTACKNavigator
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
        self._opsec_engine = OPSECEngine()
        self._traffic_profiler = TrafficProfiler()
        self._signature_evader = SignatureEvader()
        self._lolbin_engine = LOLBinEngine()
        self._attack_mapper = ATTACKMapper()
        self._attack_navigator = ATTACKNavigator(self._attack_mapper)
        self._router = CyberTaskRouter(
            ollama_client, tool_registry, self._command_planner,
            opsec_engine=self._opsec_engine,
            signature_evader=self._signature_evader,
            lolbin_engine=self._lolbin_engine,
        )
        self._analyst = Analyst(ollama_client)
        self._verifier = Verifier(ollama_client)
        self._memory = MemoryManager()
        self._poc_generator = POCGenerator(ollama_client)
        self._poc_callbacks: list[Callable] = []
        self._stealth_mode: bool = False
        self._stealth_callbacks: list[Callable] = []

        self._state = OrchestratorState()
        self._reasoning_callbacks: list[Callable] = []
        self._on_approval_required: Callable | None = None
        self._approval_response: bool | None = None
        self._command_started_callbacks: list[Callable] = []
        self._command_finished_callbacks: list[Callable] = []
        self._command_result_callbacks: list[Callable] = []

    @property
    def state(self) -> OrchestratorState:
        return self._state

    @property
    def memory(self) -> MemoryManager:
        return self._memory

    def on_reasoning_update(self, callback: Callable) -> None:
        self._reasoning_callbacks.append(callback)

    def on_command_started(self, callback: Callable) -> None:
        self._command_started_callbacks.append(callback)

    def on_command_finished(self, callback: Callable) -> None:
        self._command_finished_callbacks.append(callback)

    def on_command_result(self, callback: Callable) -> None:
        self._command_result_callbacks.append(callback)

    def on_poc_generated(self, callback: Callable) -> None:
        self._poc_callbacks.append(callback)

    def on_stealth_update(self, callback: Callable) -> None:
        """Register callback for stealth/OPSEC updates."""
        self._stealth_callbacks.append(callback)

    @property
    def stealth_mode(self) -> bool:
        return self._stealth_mode

    @stealth_mode.setter
    def stealth_mode(self, value: bool) -> None:
        self._stealth_mode = value
        self._opsec_engine.stealth_mode = value
        self._planner.stealth_mode = value
        self._router.stealth_mode = value
        if value:
            self._traffic_profiler.set_profile("careful")
        else:
            self._traffic_profiler.set_profile("aggressive")
        logger.info("Orchestrator stealth mode: %s", "ENGAGED" if value else "disengaged")
        self._emit_stealth_update()

    @property
    def attack_mapper(self) -> ATTACKMapper:
        return self._attack_mapper

    @property
    def attack_navigator(self) -> ATTACKNavigator:
        return self._attack_navigator

    @property
    def opsec_engine(self) -> OPSECEngine:
        return self._opsec_engine

    @property
    def lolbin_engine(self) -> LOLBinEngine:
        return self._lolbin_engine

    @property
    def traffic_profiler(self) -> TrafficProfiler:
        return self._traffic_profiler

    def _emit_stealth_update(self) -> None:
        data = {
            "stealth_mode": self._stealth_mode,
            "opsec_summary": self._opsec_engine.get_opsec_summary(),
            "traffic_stats": self._traffic_profiler.get_statistics(),
            "attack_coverage": self._attack_mapper.get_coverage_summary(),
        }
        for cb in self._stealth_callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error("Stealth callback error: %s", e)

    def _emit_poc_generated(self, pocs: list) -> None:
        for cb in self._poc_callbacks:
            try:
                cb(pocs)
            except Exception as e:
                logger.error('POC callback error: %s', e)

    def _emit_command_started(self, tool: str, backend: str, cmd: str) -> None:
        for cb in self._command_started_callbacks:
            try:
                cb(tool, backend, cmd)
            except Exception as e:
                logger.error("Command started callback error: %s", e)

    def _emit_command_finished(self, tool: str, success: bool, duration: float) -> None:
        for cb in self._command_finished_callbacks:
            try:
                cb(tool, success, duration)
            except Exception as e:
                logger.error("Command finished callback error: %s", e)

    def _emit_command_result(self, result: dict) -> None:
        for cb in self._command_result_callbacks:
            try:
                cb(result)
            except Exception as e:
                logger.error("Command result callback error: %s", e)

    def set_approval_handler(self, handler: Callable) -> None:
        self._on_approval_required = handler

    def submit_approval_decision(self, approved: bool) -> None:
        self._approval_response = approved

    def _update_reasoning(self, step: str, status: str, detail: str = "") -> None:
        existing = None
        for s in self._state.reasoning_steps:
            if s.step == step:
                existing = s
                break

        if existing:
            existing.status = status
            existing.detail = detail
        else:
            self._state.reasoning_steps.append(ReasoningStep(
                step=step,
                status=status,
                detail=detail,
            ))

        steps_data = [s.model_dump() for s in self._state.reasoning_steps]
        for cb in self._reasoning_callbacks:
            try:
                cb(steps_data)
            except Exception as e:
                logger.error("Reasoning callback error: %s", e)

    async def process_request(self, user_request: str) -> str:
        if self._kill_switch.is_engaged:
            return "Operation blocked: Emergency kill switch is active."

        investigation_id = f"inv_{uuid.uuid4().hex[:8]}"
        self._state = OrchestratorState(
            investigation_id=investigation_id,
            is_running=True,
        )

        inv_memory = self._memory.get_investigation(investigation_id)

        self._memory.conversation.add_message("user", user_request)

        try:
            self._update_reasoning("UNDERSTANDING REQUEST", "active", "Analyzing intent and scope")

            scope_text = self._format_scope()

            plan = await self._planner.plan_task(
                user_request=user_request,
                context_summary=self._memory.conversation.get_context_summary(),
                scope_constraints=scope_text,
            )

            self._update_reasoning(
                "UNDERSTANDING REQUEST",
                "complete",
                f"Intent: {plan.intent}",
            )

            self._update_reasoning(
                "TASK PLAN",
                "active",
                f"{len(plan.phases)} phases planned",
            )

            for p in plan.phases:
                self._update_reasoning(
                    f"PHASE {p.phase_number}: {p.name}",
                    "pending",
                    p.description,
                )

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

                    if self._stealth_mode and tool_selection.command_plan:
                        opsec_score = self._opsec_engine.evaluate_command(
                            tool_selection.command_plan.executable,
                            tool_selection.command_plan.arguments,
                            plan.target,
                        )
                        self._update_reasoning(
                            f"OPSEC: {tool_selection.tool_name}",
                            "active",
                            f"OPSEC Score: {opsec_score.total_score}/100 ({opsec_score.risk_label})",
                        )
                        if self._opsec_engine.should_block_in_stealth(opsec_score):
                            fallback = self._opsec_engine.resolve_stealth_fallback(
                                tool_selection.command_plan.executable,
                                tool_selection.command_plan.arguments,
                                plan.target,
                            )
                            if fallback:
                                original_tool = tool_selection.tool_name
                                alt_exec, alt_args = fallback
                                alt_score = self._opsec_engine.evaluate_command(alt_exec, alt_args, plan.target)
                                tool_selection.tool_name = alt_exec
                                tool_selection.command_plan = CommandPlan(
                                    executable=alt_exec,
                                    arguments=alt_args,
                                    target=plan.target,
                                    timeout=tool_selection.command_plan.timeout,
                                    backend="wsl2",
                                    explanation=f"Stealth fallback replacing {original_tool}",
                                    risk_level="LOW_RISK",
                                )
                                self._update_reasoning(
                                    f"OPSEC: {alt_exec}",
                                    "complete",
                                    f"Switched from {original_tool} (OPSEC {opsec_score.total_score}) "
                                    f"to {alt_exec} (OPSEC {alt_score.total_score})",
                                )
                            else:
                                self._update_reasoning(
                                    f"OPSEC: {tool_selection.tool_name}",
                                    "blocked",
                                    f"OPSEC score {opsec_score.total_score} exceeds stealth threshold",
                                )
                                blocked_reasons.append(
                                    f"OPSEC: {tool_selection.tool_name} blocked (score: {opsec_score.total_score})"
                                )
                                continue
                        self._update_reasoning(
                            f"OPSEC: {tool_selection.tool_name}",
                            "complete",
                            f"OPSEC Score: {opsec_score.total_score}/100 ({opsec_score.risk_label})",
                        )

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

                    if self._stealth_mode:
                        jitter = await self._traffic_profiler.apply_jitter()
                        if jitter > 0:
                            self._update_reasoning(
                                f"STEALTH JITTER",
                                "complete",
                                f"Applied {jitter:.1f}s jitter delay",
                            )

                    self._audit.log_command_execution(
                        task_id=investigation_id,
                        execution_id="",
                        tool_name=tool_selection.tool_name,
                        target=plan.target,
                        command=tool_selection.command_plan.to_command_string(),
                        policy_decision=policy.risk,
                        risk_level=policy.risk,
                    )

                    self._emit_command_started(
                        tool_selection.tool_name,
                        tool_selection.command_plan.backend,
                        tool_selection.command_plan.to_command_string(),
                    )

                    exec_request = ExecutionRequest(
                        task_id=investigation_id,
                        command_plan=tool_selection.command_plan,
                    )
                    exec_result = await self._exec_manager.execute(exec_request)

                    self._emit_command_finished(
                        tool_selection.tool_name,
                        exec_result.status == ExecutionStatus.COMPLETED,
                        exec_result.duration_seconds,
                    )

                    result_payload = exec_result.model_dump()
                    result_payload["status"] = exec_result.status.value
                    result_payload["target"] = plan.target
                    self._emit_command_result(result_payload)

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

                        attack_mappings = self._attack_mapper.record_execution(
                            tool_selection.tool_name, status="completed"
                        )
                        if attack_mappings:
                            techniques = ", ".join(m.technique_id for m in attack_mappings[:3])
                            self._update_reasoning(
                                f"ATT&CK: {tool_selection.tool_name}",
                                "complete",
                                f"Techniques: {techniques}",
                            )

                        if self._stealth_mode:
                            self._traffic_profiler.record_execution()

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

                        self._update_reasoning("GENERATING POC", "active", f"Creating POC for {tool_selection.tool_name}")
                        try:
                            poc_entries = await self._poc_generator.generate_poc(
                                tool_name=tool_selection.tool_name,
                                command=tool_selection.command_plan.to_command_string(),
                                raw_output=exec_result.stdout[:4000],
                                analysis=analysis,
                                target=plan.target,
                                investigation_id=investigation_id,
                            )
                            if poc_entries:
                                self._emit_poc_generated([p.model_dump() for p in poc_entries])
                                self._update_reasoning("GENERATING POC", "complete", f"{len(poc_entries)} POC(s) generated")
                            else:
                                self._update_reasoning("GENERATING POC", "complete", "No actionable findings for POC")
                        except Exception as poc_err:
                            logger.warning("POC generation failed: %s", poc_err)
                            self._update_reasoning("GENERATING POC", "failed", str(poc_err)[:200])
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
