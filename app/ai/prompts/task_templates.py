from __future__ import annotations


TASK_DECOMPOSITION_TEMPLATE = """Analyze the following cybersecurity research request and create a structured task plan.

USER REQUEST: {user_request}

CURRENT SCOPE:
{scope_info}

AVAILABLE BACKENDS: {available_backends}
AVAILABLE TOOLS: {available_tools}

Create a phased task plan. Respond with valid JSON only."""


TOOL_SELECTION_TEMPLATE = """Select the best tools for the following task phase.

PHASE: {phase_name}
DESCRIPTION: {phase_description}
CATEGORY: {category}
REQUIRED CAPABILITIES: {required_capabilities}
TARGET: {target}
RISK LIMIT: {risk_limit}

AVAILABLE TOOLS IN THIS CATEGORY:
{available_tools_detail}

INSTALLED TOOLS:
{installed_tools}

Select tools and generate structured command plans. Respond with valid JSON only."""


ANALYSIS_TEMPLATE = """Analyze the following security tool results.

INVESTIGATION CONTEXT:
{investigation_context}

TARGET: {target}

TOOL: {tool_name}
COMMAND: {command}

STRUCTURED RESULTS:
{structured_results}

RAW OUTPUT (EXCERPT):
{raw_output_excerpt}

PREVIOUSLY DISCOVERED FACTS:
{known_facts}

Provide a thorough analysis of these results. Focus on security-relevant findings."""


VERIFICATION_TEMPLATE = """Verify the following analysis against the available evidence.

ANALYSIS:
{analysis}

EVIDENCE:
{evidence}

TOOL OUTPUTS:
{tool_outputs}

Verify each conclusion and rate confidence. Respond with valid JSON only."""


OSINT_PLANNING_TEMPLATE = """Plan OSINT collection for the following target.

TARGET TYPE: {target_type}
TARGET VALUE: {target_value}

AVAILABLE CONNECTORS:
{available_connectors}

KNOWN INFORMATION:
{known_info}

Plan which connectors to query and how to correlate results. Respond with valid JSON only."""


FINAL_REPORT_TEMPLATE = """Generate a comprehensive security research report.

INVESTIGATION: {investigation_name}
TARGET: {target}

PHASES COMPLETED:
{phases_summary}

ALL FINDINGS:
{all_findings}

OSINT DATA:
{osint_data}

KNOWLEDGE GRAPH SUMMARY:
{graph_summary}

VERIFIED CONCLUSIONS:
{verified_conclusions}

Generate a clear, professional security report with:
1. Executive summary
2. Target overview
3. Key findings (ordered by severity)
4. Detailed technical findings
5. OSINT intelligence
6. Recommendations
7. Evidence references"""


COMMAND_VALIDATION_TEMPLATE = """Validate the following command before execution.

EXECUTABLE: {executable}
ARGUMENTS: {arguments}
TARGET: {target}
BACKEND: {backend}
EXPLANATION: {explanation}

TOOL DOCUMENTATION:
{tool_documentation}

AUTHORIZED SCOPE:
{authorized_scope}

SECURITY POLICY:
{security_policy}

Validate this command and classify its risk. Respond with valid JSON only."""
