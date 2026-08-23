"""Node functions and MCPManager for the audit agent."""

import json
import os
import re
from contextlib import AsyncExitStack
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .prompts import (
    ACT_PROMPT,
    ACT_SUFFICIENCY_PROMPT,
    PLAN_PROMPT,
    SYNTHESIZE_PROMPT,
    SYSTEM_PROMPT,
    WORKPAPER_PROMPT,
)
from .state import AgentState

# TODO: Update this path to your bolt conda env python
# Run `which python` inside the activated bolt env to find it
PYTHON_PATH = os.environ.get(
    "BOLT_PYTHON_PATH",
    os.path.expanduser("~/opt/anaconda3/envs/bolt/bin/python"),
)

MODEL = "claude-sonnet-4-6"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MCP_SERVERS = {
    "ledger_db": os.path.join(BASE_DIR, "mcp_servers", "ledger_db", "server.py"),
    "evidence_registry": os.path.join(BASE_DIR, "mcp_servers", "evidence_registry", "server.py"),
    "criteria_rag": os.path.join(BASE_DIR, "mcp_servers", "criteria_rag", "server.py"),
    "workpaper_rag": os.path.join(BASE_DIR, "mcp_servers", "workpaper_rag", "server.py"),
}


def _is_overloaded(exc: BaseException) -> bool:
    return hasattr(exc, "status_code") and exc.status_code == 529


class MCPManager:
    """Async context manager that launches all MCP servers, discovers tools, and routes calls."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._tool_map: dict[str, str] = {}  # tool_name -> server_name
        self._tool_schemas: list[dict] = []
        self._exit_stack: AsyncExitStack | None = None

    async def __aenter__(self):
        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        for server_name, server_path in MCP_SERVERS.items():
            params = StdioServerParameters(
                command=PYTHON_PATH,
                args=[server_path],
            )

            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(params)
            )
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()

            self._sessions[server_name] = session

            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self._tool_map[tool.name] = server_name
                self._tool_schemas.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": tool.inputSchema,
                })

        return self

    async def __aexit__(self, *exc):
        if self._exit_stack:
            await self._exit_stack.__aexit__(*exc)

    @property
    def tool_schemas(self) -> list[dict]:
        return self._tool_schemas

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        server_name = self._tool_map.get(tool_name)
        if not server_name:
            return f"Error: Unknown tool '{tool_name}'"
        session = self._sessions[server_name]
        result = await session.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else "(no output)"


# Global reference set by run_procedure in graph.py
_mcp_manager: MCPManager | None = None


def set_mcp_manager(manager: MCPManager):
    global _mcp_manager
    _mcp_manager = manager


def get_mcp_manager() -> MCPManager:
    if _mcp_manager is None:
        raise RuntimeError("MCPManager not initialized")
    return _mcp_manager


def _get_llm(max_tokens: int = 4096):
    return ChatAnthropic(model=MODEL, max_tokens=max_tokens)


@retry(
    retry=retry_if_exception(_is_overloaded),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
)
async def _invoke_llm(messages: list, max_tokens: int = 4096) -> AIMessage:
    llm = _get_llm(max_tokens=max_tokens)
    return await llm.ainvoke(messages)


@retry(
    retry=retry_if_exception(_is_overloaded),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
)
async def _invoke_llm_with_tools(messages: list, tools: list) -> AIMessage:
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(tools)
    return await llm_with_tools.ainvoke(messages)


def _format_evidence(evidence: dict) -> str:
    if not evidence:
        return "(none gathered yet)"
    parts = []
    for key, value in evidence.items():
        if isinstance(value, list):
            parts.append(f"[{key}]: {len(value)} call(s)")
            for item in value:
                if isinstance(item, dict) and "result" in item:
                    parts.append(f"  args: {json.dumps(item.get('args', {}))}")
                    parts.append(f"  result:\n{item['result']}")
                    parts.append("")
                else:
                    parts.append(f"  • {str(item)}")
        else:
            parts.append(f"[{key}]:\n{str(value)}")
    return "\n".join(parts)


async def plan_node(state: AgentState) -> dict:
    procedure = state["procedure"]
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=PLAN_PROMPT.format(procedure=json.dumps(procedure, indent=2))),
    ]
    response = await _invoke_llm(messages)
    plan = response.content

    return {
        "plan": plan,
        "reasoning_trace": [f"[PLAN] {plan}"],
        "act_count": 0,
    }


async def act_node(state: AgentState) -> dict:
    manager = get_mcp_manager()
    act_count = state.get("act_count", 0) + 1
    evidence = state.get("evidence", {})

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=ACT_PROMPT.format(
            act_count=act_count,
            plan=state.get("plan", ""),
            evidence=_format_evidence(evidence),
        )),
    ]

    lc_tools = []
    for schema in manager.tool_schemas:
        lc_tools.append({
            "name": schema["name"],
            "description": schema["description"],
            "input_schema": schema["input_schema"],
        })

    response = await _invoke_llm_with_tools(messages, lc_tools)

    new_tool_calls = []
    new_evidence: dict[str, Any] = {}
    trace_lines = [f"[ACT round {act_count}]"]

    if response.tool_calls:
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            trace_lines.append(f"  Calling {tool_name}({json.dumps(tool_args)})")

            result = await manager.call_tool(tool_name, tool_args)

            dedup_key = f"{tool_name}_{json.dumps(tool_args, sort_keys=True)}"
            new_tool_calls.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
                "dedup_key": dedup_key,
            })

            evidence_key = tool_name
            if evidence_key not in new_evidence:
                new_evidence[evidence_key] = []
            new_evidence[evidence_key].append({
                "args": tool_args,
                "result": result,
            })

            trace_lines.append(f"  → {result[:200]}...")
    else:
        trace_lines.append("  (no tool calls made)")

    return {
        "tool_calls": new_tool_calls,
        "evidence": new_evidence,
        "reasoning_trace": trace_lines,
        "act_count": act_count,
    }


async def should_continue_acting(state: AgentState) -> str:
    act_count = state.get("act_count", 0)

    if act_count >= 3:
        return "synthesize"

    evidence = state.get("evidence", {})
    procedure = state["procedure"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=ACT_SUFFICIENCY_PROMPT.format(
            procedure=json.dumps(procedure, indent=2),
            evidence=_format_evidence(evidence),
            act_count=act_count,
        )),
    ]

    response = await _invoke_llm(messages)
    answer = response.content.strip()

    if answer.startswith("SUFFICIENT"):
        return "synthesize"
    return "act"


async def synthesize_node(state: AgentState) -> dict:
    procedure = state["procedure"]
    evidence = state.get("evidence", {})

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=SYNTHESIZE_PROMPT.format(
            procedure=json.dumps(procedure, indent=2),
            evidence=_format_evidence(evidence),
        )),
    ]

    response = await _invoke_llm(messages)
    synthesis = response.content

    return {
        "reasoning_trace": [f"[SYNTHESIZE] {synthesis}"],
        "evidence": {"synthesis": synthesis},
    }


async def workpaper_node(state: AgentState) -> dict:
    procedure = state["procedure"]
    evidence = state.get("evidence", {})
    synthesis = evidence.get("synthesis", "")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=WORKPAPER_PROMPT.format(
            procedure=json.dumps(procedure, indent=2),
            synthesis=synthesis,
            evidence=_format_evidence(evidence),
        )),
    ]

    response = await _invoke_llm(messages, max_tokens=8192)
    raw = response.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

    try:
        workpaper = json.loads(raw)
    except json.JSONDecodeError:
        workpaper = {
            "objective": procedure.get("objective", ""),
            "assertion": procedure.get("assertion", ""),
            "control_id": procedure.get("control_id", ""),
            "procedure_performed": "Error: could not parse workpaper JSON from LLM output",
            "population_summary": "",
            "sample": "",
            "exceptions": [],
            "deviation_rate": "N/A",
            "criteria_cited": [],
            "prior_year_reference": [],
            "preliminary_conclusion": "Workpaper generation encountered a parsing error. Raw output preserved in reasoning trace.",
            "judgment_note": "Auditor should review raw output in reasoning trace.",
            "recommended_disposition": "ESCALATE — Auditor judgment required",
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "_raw_output": raw,
        }

    # Validate: recommended_disposition must end with "— Auditor judgment required"
    disposition = workpaper.get("recommended_disposition", "")
    if not disposition.endswith("— Auditor judgment required"):
        workpaper["recommended_disposition"] = f"{disposition} — Auditor judgment required"

    if "prepared_at" not in workpaper:
        workpaper["prepared_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "workpaper": workpaper,
        "reasoning_trace": [f"[WORKPAPER] Drafted — disposition: {workpaper.get('recommended_disposition', 'UNKNOWN')}"],
    }
