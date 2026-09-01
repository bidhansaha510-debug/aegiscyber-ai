from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.ai.ollama_client import OllamaClient
from app.ai.planner import Planner, TaskPlan, TaskPhase
from app.ai.router import CyberTaskRouter, RoutingResult
from app.ai.analyst import Analyst
from app.ai.verifier import Verifier
from app.ai.memory import MemoryManager
from app.ai.prompts.system_prompts import (
    COMMAND_HEAL_SYSTEM,
    ORCHESTRATOR_SYSTEM,
    WEAPON_ORCHESTRATOR_SYSTEM,
    WEAPON_PLANNER_SYSTEM,
    WEAPON_FINAL_REPORT_SYSTEM,
)
from app.ai.prompts.task_templates import FINAL_REPORT_TEMPLATE
from app.config import get_config
from pathlib import Path
from app.execution.manager import ExecutionManager
from app.execution.models import CommandPlan, ExecutionRequest, ExecutionResult, ExecutionStatus, PolicyDecision
from app.tools.registry import ToolRegistry
from app.tools.policy import PolicyEngine
from app.tools.command_planner import CommandPlanner
from app.tools.auto_installer import ToolAutoInstaller
from app.parsers.registry import ParserRegistry
from app.osint.engine import OSINTEngine
from app.osint.models import OSINTSearchRequest, EntityType
from app.security.authorization import AuthorizationManager
from app.security.audit import AuditLogger
from app.security.kill_switch import KillSwitch
from app.ai.poc_generator import POCGenerator
from app.ai.json_utils import try_parse_json
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
        self._auto_installer = ToolAutoInstaller(execution_manager, tool_registry)
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
        self._weapon_config = get_config()
        self._weapon_mode: bool = bool(self._weapon_config.weapon.weapon_mode_default)
        if self._weapon_mode:
            self._policy_engine.weapon_mode = True
            self._poc_generator.weapon_mode = True
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
    def weapon_mode(self) -> bool:
        return self._weapon_mode

    @weapon_mode.setter
    def weapon_mode(self, value: bool) -> None:
        self._weapon_mode = value
        self._policy_engine.weapon_mode = value
        self._poc_generator.weapon_mode = value
        logger.info("Orchestrator weapon mode: %s", "ARMED" if value else "SAFE")

    @property
    def poc_generator(self) -> POCGenerator:
        return self._poc_generator

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
                system_prompt=WEAPON_PLANNER_SYSTEM if self._weapon_mode else "",
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
            request_pocs: list[Any] = []

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

                    heal_cfg = self._weapon_config.selfheal
                    max_attempts = (heal_cfg.max_retries + 1) if heal_cfg.enabled else 1
                    current_plan = tool_selection.command_plan
                    attempt = 0
                    while True:
                        self._audit.log_command_execution(
                            task_id=investigation_id,
                            execution_id="",
                            tool_name=tool_selection.tool_name,
                            target=plan.target,
                            command=current_plan.to_command_string(),
                            policy_decision=policy.risk,
                            risk_level=policy.risk,
                        )

                        self._emit_command_started(
                            tool_selection.tool_name,
                            current_plan.backend,
                            current_plan.to_command_string(),
                        )

                        exec_request = ExecutionRequest(
                            task_id=investigation_id,
                            command_plan=current_plan,
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

                        if not self._should_self_heal(exec_result):
                            break
                        if self._kill_switch.is_engaged:
                            break
                        attempt += 1
                        if attempt > max_attempts:
                            break

                        healed = await self._self_heal_command(
                            exec_result,
                            current_plan,
                            tool_selection.tool_name,
                            plan.target,
                            investigation_id,
                        )
                        if healed is None:
                            break
                        healed_plan, heal_action = healed

                        if heal_action == "retry_healed":
                            healed_policy = self._policy_engine.evaluate(
                                healed_plan,
                                tool_def,
                                investigation_id,
                            )
                            if not healed_policy.allowed:
                                blocked_reasons.append(healed_policy.reason)
                                self._update_reasoning(
                                    f"TOOL: {tool_selection.tool_name}",
                                    "blocked",
                                    f"Healed command blocked: {healed_policy.reason}",
                                )
                                break
                            if healed_policy.requires_approval:
                                self._update_reasoning(
                                    f"TOOL: {tool_selection.tool_name}",
                                    "awaiting_approval",
                                    f"Healed command risk: {healed_policy.risk} - Requires approval",
                                )
                                approved = await self._request_approval(healed_plan, healed_policy)
                                if not approved:
                                    self._update_reasoning(
                                        f"TOOL: {tool_selection.tool_name}",
                                        "skipped",
                                        "User declined healed command",
                                    )
                                    break

                        current_plan = healed_plan

                    tool_selection.command_plan = current_plan

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
                                request_pocs.extend(poc_entries)
                                if self._weapon_mode:
                                    self._update_reasoning("GENERATING POC", "complete", f"{len(poc_entries)} exploit POC(s) generated - executing")
                                    await self._run_generated_exploits(poc_entries, plan, investigation_id)
                                    self._emit_poc_generated([p.model_dump() for p in poc_entries])
                                else:
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
                final_report = await self._analyst.summarize_findings(
                    all_findings,
                    plan.target,
                    system_prompt=WEAPON_FINAL_REPORT_SYSTEM if self._weapon_mode else "",
                )
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

            exploit_appendix = self._build_exploit_appendix(request_pocs)
            if exploit_appendix:
                final_report = final_report.rstrip() + "\n\n---\n\n" + exploit_appendix

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

        system_prompt = WEAPON_ORCHESTRATOR_SYSTEM if self._weapon_mode else ORCHESTRATOR_SYSTEM
        messages = [
            {"role": "system", "content": system_prompt}
        ] + self._memory.conversation.get_chat_messages()

        response = await self._ollama.chat(messages=messages)
        if not response:
            response = "I'm unable to respond right now. Please check that Ollama is running."

        self._memory.conversation.add_message("assistant", response)
        return response

    def _to_wsl_path(self, windows_path: str) -> str:
        try:
            p = Path(windows_path).resolve()
            drive = p.drive.rstrip(":").lower()
            if not drive:
                return windows_path.replace("\\", "/")
            sub = str(p).split(":", 1)[1].replace("\\", "/")
            return f"/mnt/{drive}{sub}"
        except Exception:
            return ""

    async def _run_generated_exploits(self, pocs: list, plan: TaskPlan, investigation_id: str) -> None:
        if not self._weapon_config.weapon.execute_exploits:
            self._update_reasoning("EXPLOIT EXECUTION", "skipped", "execute_exploits disabled in config")
            return
        if not self._exec_manager.is_backend_available("wsl2"):
            self._update_reasoning("EXPLOIT EXECUTION", "skipped", "WSL2 backend unavailable")
            return

        limit = self._weapon_config.weapon.max_exploit_executions_per_request
        executed = 0
        for poc in pocs:
            if self._kill_switch.is_engaged:
                self._update_reasoning("EXPLOIT EXECUTION", "stopped", "Kill switch engaged")
                break
            if executed >= limit:
                self._update_reasoning(
                    "EXPLOIT EXECUTION", "complete",
                    f"Execution limit reached ({limit})",
                )
                break
            if not poc.exploit_file:
                continue

            wsl_path = self._to_wsl_path(poc.exploit_file)
            if not wsl_path:
                continue

            ext = Path(poc.exploit_file).suffix.lower()
            if ext == ".py":
                executable, arguments = "python3", [wsl_path]
            elif ext == ".sh":
                executable, arguments = "bash", [wsl_path]
            else:
                continue

            exploit_plan = CommandPlan(
                executable=executable,
                arguments=arguments,
                target=plan.target,
                timeout=self._weapon_config.weapon.exploit_timeout,
                backend="wsl2",
                explanation=f"Weapon mode: executing generated exploit for '{poc.title}'",
            )

            policy = self._policy_engine.evaluate(exploit_plan, None, investigation_id)
            if not policy.allowed:
                self._update_reasoning(
                    f"EXPLOIT: {poc.title}", "blocked", policy.reason,
                )
                continue

            executed += 1
            self._audit.log_command_execution(
                task_id=investigation_id,
                execution_id="",
                tool_name=f"exploit:{poc.title[:60]}",
                target=plan.target,
                command=exploit_plan.to_command_string(),
                policy_decision=policy.risk,
                risk_level="HIGH_RISK",
            )
            self._emit_command_started(
                f"EXPLOIT: {poc.title[:40]}", "wsl2", exploit_plan.to_command_string(),
            )
            self._update_reasoning(
                f"EXPLOIT: {poc.title}", "running",
                f"Executing {wsl_path} against {plan.target}",
            )

            exec_request = ExecutionRequest(
                task_id=investigation_id,
                command_plan=exploit_plan,
            )
            exec_result = await self._exec_manager.execute(exec_request)

            success = (
                exec_result.status == ExecutionStatus.COMPLETED
                and exec_result.exit_code == 0
            )
            evidence = (exec_result.stdout or exec_result.stderr or exec_result.error_message)[:2000]
            poc.exploitation_success = success
            poc.exploitation_result = (
                f"status={exec_result.status.value} exit_code={exec_result.exit_code}\n"
                f"{evidence}"
            )

            self._emit_command_finished(
                f"EXPLOIT: {poc.title[:40]}", success, exec_result.duration_seconds,
            )
            result_payload = exec_result.model_dump()
            result_payload["status"] = exec_result.status.value
            result_payload["target"] = plan.target
            self._emit_command_result(result_payload)

            self._update_reasoning(
                f"EXPLOIT: {poc.title}",
                "complete" if success else "failed",
                ("Exploitation succeeded" if success else "Exploitation failed")
                + f" in {exec_result.duration_seconds:.1f}s",
            )

            if self._weapon_config.weapon.verify_exploitation and exec_result.stdout:
                verification = await self._analyst.analyze(
                    tool_name=f"exploit:{poc.title[:60]}",
                    command=exploit_plan.to_command_string(),
                    structured_results={"exploitation_success": success},
                    raw_output=exec_result.stdout[:4000],
                    target=plan.target,
                    investigation_context=f"Verify exploitation result for: {poc.title}",
                    known_facts="",
                )
                poc.exploitation_result += "\n--- verification ---\n" + verification[:2000]

    async def _request_approval(self, command_plan: CommandPlan, policy: PolicyDecision) -> bool:
        if self._weapon_mode and self._weapon_config.weapon.auto_approve_all_risk:
            logger.info("WEAPON MODE: auto-approved %s", command_plan.to_command_string()[:120])
            return True
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

    def _deterministic_heal(
        self, plan: CommandPlan, error_text: str
    ) -> tuple[CommandPlan, str] | None:
        """Fix common command errors without an LLM round-trip.

        Returns (fixed_plan, reason) when a known error class was handled,
        otherwise None so the caller falls through to auto-install / LLM heal.
        """
        executable = (plan.executable or "").strip().lower()
        args = [str(a) for a in plan.arguments]
        target = (plan.target or "").strip()
        changed = False
        reason = ""
        text = error_text or ""
        low = text.lower()

        # 1. Unknown/invalid option -> drop the bad flag (and its value if separate).
        bad_opt = None
        m = re.search(r"(?:unrecognized option|invalid option)\s+['\"`]*-{1,2}([A-Za-z0-9][\w=-]*)", low)
        if not m:
            m = re.search(r"option\s+['\"]?(-{1,2}[\w=-]+)['\"]?[^\n]{0,40}(?:is unknown|unknown option)", low)
        if m:
            bad = m.group(1).lstrip("-=")
            bad_opt = bad

        if bad_opt:
            filtered: list[str] = []
            skip_next = False
            for a in args:
                if skip_next and not str(a).startswith("-"):
                    skip_next = False
                    changed = True
                    continue
                skip_next = False
                core = str(a).lstrip("-=")
                if str(a).startswith("-") and (core == bad_opt or core.startswith(bad_opt + "=")):
                    changed = True
                    reason = f"removed invalid option '{a}'"
                    # A boolean-only flag cannot consume a value; treat single-letter
                    # flags and long flags that took a separate token as valueless.
                    if len(core) <= 1:
                        skip_next = True
                    continue
                filtered.append(a)
            args = filtered

        # 2. dig: dead resolver -> force a reliable one.
        if executable == "dig" and (
            "couldn't get address" in low
            or "communications error" in low
            or "no servers could be reached" in low
            or "connection timed out" in low
            or "no response from servers" in low
        ):
            args = [a for a in args if not str(a).startswith("@")]
            if "@8.8.8.8" not in args:
                args.insert(0, "@8.8.8.8")
            changed = True
            reason = "replaced dead DNS resolver with @8.8.8.8"

        # 3. Usage errors caused by a missing target -> append it.
        if "usage" in low and target:
            joined = " ".join(args).lower()
            if target.lower() not in joined and target.lower() not in executable:
                args.append(target)
                changed = True
                reason = "appended missing target argument"

        # 4. Timeouts on nmap -> reduce timing aggressiveness.
        if ("timed out" in low or "timeout" in low) and executable == "nmap":
            if any(re.fullmatch(r"-T[45]", a) for a in args):
                args = ["-T3" if re.fullmatch(r"-T[45]", a) else a for a in args]
                changed = True
                reason = "reduced nmap timing T4/T5 -> T3 after timeout"
            elif "--max-retries" not in args:
                args += ["--max-retries", "1"]
                changed = True
                reason = "added --max-retries 1 after timeout"

        # 5. nmap privileges on WSL: TCP scan flags failed -> fall back to -sT.
        if executable == "nmap" and (
            "operation not permitted" in low or "you requested a scan type" in low
        ):
            if not any(a in ("-sT", "-sP", "-sn", "-sU") for a in args):
                args = ["-sT" if a in ("-sS", "-sN", "-sF", "-sX") else a for a in args]
                if not any(a.startswith("-s") for a in args):
                    args.insert(0, "-sT")
                changed = True
                reason = "switched to unprivileged TCP connect scan (-sT)"

        if not changed:
            return None

        fixed = plan.model_copy(deep=True)
        fixed.arguments = args
        return (fixed, reason)

    def _should_self_heal(self, exec_result: ExecutionResult) -> bool:
        """Heal whenever a command did not complete successfully.

        NOTE: many tools (nikto, dig, nmap with errors, curl) print their error
        text to STDOUT, not stderr - so a non-empty stdout must NOT suppress
        healing. The retry budget (selfheal.max_retries) caps the loop, so
        healing every non-completed execution is safe.
        """
        return exec_result.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT)

    def _collect_error_text(self, exec_result: ExecutionResult) -> str:
        parts = [exec_result.error_message or "", exec_result.stderr or "", exec_result.stdout or ""]
        text = "\n".join(p for p in parts if p).strip()
        return text[-2000:] if len(text) > 2000 else text

    async def _self_heal_command(
        self,
        exec_result: ExecutionResult,
        failed_plan: CommandPlan,
        tool_name: str,
        target: str,
        investigation_id: str,
    ) -> tuple[CommandPlan | None, str | None]:
        error_text = self._collect_error_text(exec_result)

        error_lower = error_text.lower()
        heal_cfg = self._weapon_config.selfheal

        # Fast path: recognise common error classes and fix them directly
        # without a (slow, unreliable) LLM round-trip.
        deterministic = self._deterministic_heal(failed_plan, error_text)
        if deterministic is not None:
            self._update_reasoning(
                f"SELF-HEAL: {tool_name}", "active",
                f"Applying deterministic fix: {deterministic[1]}",
            )
            return (deterministic[0], "retry_healed")

        if heal_cfg.auto_install_tools:
            missing = self._auto_installer.extract_missing_binary(
                exec_result, failed_plan.executable
            )
            if missing and self._auto_installer.is_missing_tool_error(
                exec_result, failed_plan.backend
            ):
                self._update_reasoning(
                    f"AUTO-INSTALL: {missing}", "active",
                    f"Missing tool detected - installing '{missing}'",
                )
                try:
                    installed, msg = await self._auto_installer.install_tool(
                        missing, failed_plan.backend, investigation_id,
                    )
                except Exception as install_err:
                    installed, msg = False, str(install_err)
                if installed:
                    self._update_reasoning(
                        f"AUTO-INSTALL: {missing}", "complete",
                        f"Tool installed successfully - retrying command",
                    )
                    return (failed_plan.model_copy(deep=True), "retry_install")
                self._update_reasoning(
                    f"AUTO-INSTALL: {missing}", "failed",
                    f"Install failed: {msg[:200]}",
                )

        self._update_reasoning(
            f"SELF-HEAL: {tool_name}", "active",
            f"Command failed - generating replacement",
        )
        healed = await self._generate_healed_command(failed_plan, error_text=error_text, target=target)
        if healed is None:
            self._update_reasoning(
                f"SELF-HEAL: {tool_name}", "failed",
                "Could not generate a replacement command",
            )
            return None
        self._update_reasoning(
            f"SELF-HEAL: {tool_name}", "complete",
            f"Retrying with: {healed.to_command_string()[:120]}",
        )
        return (healed, "retry_healed")

    async def _generate_healed_command(
        self,
        failed_plan: CommandPlan,
        error_text: str,
        target: str,
    ) -> CommandPlan | None:
        prompt = (
            f"The following command failed. Read the error and produce a corrected "
            f"replacement command that achieves the same objective.\n\n"
            f"FAILED COMMAND:\n{failed_plan.to_command_string()}\n\n"
            f"TARGET: {target or failed_plan.target or 'unknown'}\n"
            f"BACKEND: {failed_plan.backend}\n\n"
            f"ERROR OUTPUT:\n{error_text or '(no error text captured)'}\n\n"
            f"Respond ONLY with the JSON object described in the system prompt."
        )
        try:
            response = await self._ollama.generate(
                prompt=prompt,
                system=COMMAND_HEAL_SYSTEM,
                temperature=0.1,
            )
        except Exception as heal_err:
            logger.warning("Self-heal LLM call failed: %s", heal_err)
            return None
        if not response:
            return None

        data, _parse_err = try_parse_json(response)
        if data is None or not isinstance(data, dict):
            return None

        executable = str(data.get("executable", "")).strip()
        if not executable:
            return None
        arguments = data.get("arguments") or []
        if not isinstance(arguments, list):
            arguments = [str(arguments)]
        arguments = [str(a) for a in arguments]
        try:
            timeout = int(data.get("timeout") or failed_plan.timeout or 0)
        except (TypeError, ValueError):
            timeout = failed_plan.timeout

        explanation = str(data.get("explanation", ""))[:300]
        try:
            healed_plan = self._command_planner.create_from_raw(
                executable,
                arguments,
                target or failed_plan.target,
                backend=failed_plan.backend,
                timeout=timeout,
                explanation=explanation or f"Self-healed replacement for: {failed_plan.to_command_string()[:100]}",
            )
        except Exception as plan_err:
            logger.warning("Failed to build healed plan: %s", plan_err)
            return None
        return healed_plan

    def _build_exploit_appendix(self, pocs: list) -> str:
        coded = [p for p in pocs if getattr(p, "exploit_code", "") and p.exploit_code.strip()]
        if not coded:
            return ""
        lines: list[str] = ["## Exploit Code", ""]
        for poc in coded:
            lines.append(f"### {poc.title}")
            if poc.usage:
                lines.append("**Usage:**")
                lines.append("```")
                lines.append(poc.usage)
                lines.append("```")
            lang = getattr(poc, "language", "") or self._guess_code_language(poc.exploit_code)
            lines.append(f"```{lang.lower() or 'text'}")
            lines.append(poc.exploit_code)
            lines.append("```")
            if getattr(poc, "exploit_file", ""):
                lines.append(f"Saved artifact: `{poc.exploit_file}`")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _guess_code_language(self, code: str, default: str = "") -> str:
        lowered = code.lstrip().lower()
        if lowered.startswith("#!") and "python" in lowered.split("\n")[0]:
            return "python"
        if "import " in code or "def " in code or "class " in code and ":" in code:
            return "python"
        if default:
            return default.lower()
        return "bash"
