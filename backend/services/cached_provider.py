"""
CachedDemoProvider — returns hard-coded GraniteOutput for the cs-demo-v1 scenario.
Used when watsonx credentials are absent or when the live call fails.
"""
from __future__ import annotations
from backend.models.schemas import GraniteOutput, GuardrailItem, SaferStep


def get() -> GraniteOutput:
    return GraniteOutput(
        workflow_gap_narrative=(
            "The official customer-support workflow documents five steps, but the actual "
            "process regularly includes seven to twelve additional activities invisible to "
            "management reporting. Manual status checks, context-repair tasks, and "
            "reconciliation steps account for a significant share of total effort, "
            "representing unplanned work that falls outside automated tracking."
        ),
        hidden_work_narrative=(
            "Agents frequently perform follow-up messages, manual CRM cross-referencing, "
            "and multi-system reconciliation that are never logged in the official workflow. "
            "Escalation and exception-handling events cluster around complex tickets and "
            "enterprise accounts, concentrating invisible workload on senior agents. "
            "These patterns indicate that automation would need robust exception routing "
            "and human oversight before meaningful time savings could be realised."
        ),
        redesign_recommendations=[
            "Introduce confidence-threshold gating so the AI escalates to a human agent "
            "whenever predicted resolution confidence falls below 0.80.",
            "Automate manual-status-check events by integrating CRM and ticketing systems "
            "so agents always see a live status without manual lookup.",
            "Add an automated context-reconstruction step that pulls relevant history "
            "into the ticket view on assignment, eliminating context-repair activities.",
            "Create a structured exception-routing procedure for tickets flagged as "
            "out-of-scope, replacing ad-hoc escalation with a defined hand-off protocol.",
            "Implement a post-resolution reconciliation job that synchronises CRM, "
            "billing, and audit systems automatically, removing manual-reconciliation steps.",
            "Preserve specialist agent involvement in duplicate-detection by running AI "
            "deduplication as a suggestion rather than an automatic merge.",
        ],
        guardrails=[
            GuardrailItem(
                id="human-approval-resolution",
                label="Human Approval on Resolution",
                type="human_approval",
                description=(
                    "Require a human agent to approve any AI-generated resolution "
                    "before it is sent to the customer."
                ),
            ),
            GuardrailItem(
                id="confidence-threshold-response",
                label="Response Confidence Threshold",
                type="confidence_threshold",
                description=(
                    "Block AI-generated first responses with model confidence below 0.80 "
                    "and route them to a human agent."
                ),
            ),
            GuardrailItem(
                id="exception-routing-escalation",
                label="Structured Exception Routing",
                type="exception_routing",
                description=(
                    "All tickets flagged as exceptions must follow a documented hand-off "
                    "procedure rather than informal escalation."
                ),
            ),
            GuardrailItem(
                id="manual-fallback-outage",
                label="Manual Fallback on AI Outage",
                type="manual_fallback",
                description=(
                    "If the AI system is unavailable, agents revert to the standard "
                    "manual workflow without disruption to customers."
                ),
            ),
            GuardrailItem(
                id="skill-preservation-rotation",
                label="Quarterly Skill-Preservation Rotation",
                type="skill_preservation",
                description=(
                    "Agents rotate through manual processing of at least 10 % of tickets "
                    "per quarter to maintain proficiency in case of AI failure."
                ),
            ),
            GuardrailItem(
                id="audit-trail-all-steps",
                label="Full Audit Trail",
                type="audit_trail",
                description=(
                    "Every AI action, human override, and escalation decision is logged "
                    "with a timestamp and actor ID for compliance review."
                ),
            ),
        ],
        safer_workflow_steps=[
            SaferStep(
                step_id="ticket-created",
                label="Ticket Created",
                executor="ai",
                requires_approval=False,
                fallback_procedure="Agent manually creates ticket in CRM if AI intake is unavailable.",
                confidence_threshold=None,
            ),
            SaferStep(
                step_id="assigned",
                label="Assigned",
                executor="ai",
                requires_approval=False,
                fallback_procedure="Agent manually routes ticket based on category and queue depth.",
                confidence_threshold=0.85,
            ),
            SaferStep(
                step_id="first-response",
                label="First Response",
                executor="hybrid",
                requires_approval=True,
                fallback_procedure="Agent writes response manually if confidence threshold not met.",
                confidence_threshold=0.80,
            ),
            SaferStep(
                step_id="exception-check",
                label="Exception Check",
                executor="hybrid",
                requires_approval=True,
                fallback_procedure="Senior agent handles exception via documented escalation procedure.",
                confidence_threshold=0.75,
            ),
            SaferStep(
                step_id="resolution",
                label="Resolution",
                executor="hybrid",
                requires_approval=True,
                fallback_procedure="Agent resolves ticket manually and documents steps taken.",
                confidence_threshold=0.80,
            ),
            SaferStep(
                step_id="auto-reconciliation",
                label="Automated Reconciliation",
                executor="ai",
                requires_approval=False,
                fallback_procedure="Agent reconciles CRM, billing, and audit log manually.",
                confidence_threshold=None,
            ),
            SaferStep(
                step_id="closed",
                label="Closed",
                executor="human",
                requires_approval=False,
                fallback_procedure=None,
                confidence_threshold=None,
            ),
        ],
        provider="cached_demo",
    )
