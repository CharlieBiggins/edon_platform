"""Sanitized vendor capability profiles for gateway configuration."""

from __future__ import annotations

from copy import deepcopy


VENDOR_PROFILES = (
    {
        "vendor_id": "openai_agents",
        "name": "OpenAI Agents",
        "protocols": ["MCP", "REST", "OTEL"],
        "preferred": ["MCP", "REST"],
        "official_docs": "https://openai.github.io/openai-agents-python/",
    },
    {
        "vendor_id": "aws_bedrock_agentcore",
        "name": "Amazon Bedrock AgentCore",
        "protocols": ["MCP", "A2A", "REST", "OTEL"],
        "preferred": ["A2A", "MCP"],
        "official_docs": "https://docs.aws.amazon.com/bedrock-agentcore/",
    },
    {
        "vendor_id": "microsoft_agent365_copilot",
        "name": "Microsoft Agent 365 and Copilot Studio",
        "protocols": ["A2A", "MCP", "REST", "OTEL"],
        "preferred": ["A2A", "MCP"],
        "official_docs": "https://learn.microsoft.com/en-us/microsoft-agent-365/",
    },
    {
        "vendor_id": "google_gemini_agent_platform",
        "name": "Google Gemini Enterprise Agent Platform",
        "protocols": ["A2A", "MCP", "REST", "OTEL"],
        "preferred": ["A2A", "MCP"],
        "official_docs": "https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent",
    },
    {
        "vendor_id": "anthropic_claude",
        "name": "Anthropic Claude",
        "protocols": ["MCP", "REST", "OTEL"],
        "preferred": ["MCP"],
        "official_docs": "https://docs.anthropic.com/en/docs/agents-and-tools/mcp",
    },
    {
        "vendor_id": "salesforce_agentforce",
        "name": "Salesforce Agentforce",
        "protocols": ["MCP", "A2A", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["REST", "MCP", "A2A"],
        "official_docs": "https://developer.salesforce.com/docs/ai/agentforce/guide/get-started.html",
    },
    {
        "vendor_id": "servicenow_agent_fabric",
        "name": "ServiceNow AI Agent Fabric",
        "protocols": ["A2A", "MCP", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["A2A", "MCP"],
        "official_docs": "https://www.servicenow.com/docs/r/intelligent-experiences/external-agent-protocols.html",
    },
    {
        "vendor_id": "uipath_agentic_automation",
        "name": "UiPath Agentic Automation",
        "protocols": ["MCP", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["MCP", "REST"],
        "official_docs": "https://docs.uipath.com/agents/automation-cloud/latest/user-guide/about-agents",
    },
    {
        "vendor_id": "langgraph",
        "name": "LangGraph",
        "protocols": ["A2A", "MCP", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["A2A", "MCP", "REST"],
        "official_docs": "https://docs.langchain.com/oss/python/langgraph/overview",
    },
    {
        "vendor_id": "epic",
        "name": "Epic",
        "protocols": ["FHIR_R4_SMART", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["FHIR_R4_SMART"],
        "official_docs": "https://open.epic.com/interface/FHIR",
    },
    {
        "vendor_id": "oracle_health",
        "name": "Oracle Health Millennium",
        "protocols": ["FHIR_R4_SMART", "REST", "WEBHOOK", "OTEL"],
        "preferred": ["FHIR_R4_SMART"],
        "official_docs": "https://docs.oracle.com/en/industries/health/millennium-platform-apis/",
    },
)


def vendor_profiles() -> list[dict]:
    return [
        {
            **deepcopy(profile),
            "status": "PROFILE_ONLY_CREDENTIALS_AND_CONFORMANCE_REQUIRED",
            "native_connector_implemented": False,
            "production_validated": False,
            "binding_authority": False,
        }
        for profile in VENDOR_PROFILES
    ]