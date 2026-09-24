#!/usr/bin/env python3
"""Renderer parsing shared by the DEV-009 rules ceiling and compiler."""

from __future__ import annotations

import json
import re
from typing import Any


EVENT_PATTERN = re.compile(
    r"^id=(?P<event_id>\S+) time=(?P<time>\d+) priority=(?P<priority>\d+) "
    r"sequence=(?P<sequence>\d+) actor=(?P<actor_id>\S+) operation=(?P<operation>\S+) "
    r"target=(?P<target>\S+) value=(?P<value>.+)$"
)


def parse_event(text: str) -> dict[str, Any]:
    match = EVENT_PATTERN.match(text.strip())
    if not match:
        raise ValueError(f"cannot parse event: {text[:120]}")
    fields = match.groupdict()
    return {
        "event_id": fields["event_id"],
        "time": int(fields["time"]),
        "priority": int(fields["priority"]),
        "sequence": int(fields["sequence"]),
        "actor_id": fields["actor_id"],
        "operation": fields["operation"],
        "target": fields["target"],
        "value": json.loads(fields["value"]),
    }


def parse_single_observation(content: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if content.startswith("{"):
        value = json.loads(content)
        if set(value) >= {"institutional_state", "event_queue"}:
            return value["institutional_state"], value["event_queue"]
        if set(value) >= {"initial_process_state", "submitted_process_events"}:
            return value["initial_process_state"], value["submitted_process_events"]
        if set(value) >= {"initial_state", "submitted_events_unordered"}:
            return value["initial_state"], value["submitted_events_unordered"]
        if set(value) >= {"typed_initial_state", "unsorted_event_matrix"}:
            return value["typed_initial_state"], value["unsorted_event_matrix"]
    if content.startswith("CHRONOLOGY_LEDGER"):
        lines = content.splitlines()
        state = json.loads(next(line.split("=", 1)[1] for line in lines if line.startswith("INITIAL_STATE=")))
        begin = lines.index("UNSORTED_ENTRIES_BEGIN") + 1
        end = lines.index("UNSORTED_ENTRIES_END")
        return state, [parse_event(line) for line in lines[begin:end]]
    if content.startswith("AUTHORIZATION_WORKPAD<"):
        state_text = content.split(" STATE::", 1)[1].split(" SUBMISSIONS::", 1)[0]
        queue = content.split(" SUBMISSIONS::", 1)[1].split(" RULE::", 1)[0]
        return json.loads(state_text), [parse_event(event) for event in queue.split(" || ")]
    if content.startswith("STATE TRANSITION CARD"):
        lines = content.splitlines()
        state = json.loads(next(line.split("Typed start: ", 1)[1] for line in lines if line.startswith("Typed start: ")))
        events = [parse_event(line[len("CARD_EVENT["):-1]) for line in lines if line.startswith("CARD_EVENT[") and line.endswith("]")]
        return state, events
    if content.startswith("DEPENDENCY_GRAPH_PACKET"):
        state_text = content.split("ROOT_STATE=", 1)[1].split(". Submitted graph events", 1)[0]
        events = re.findall(r"GRAPH_EVENT\[(.*?)\](?= GRAPH_EVENT\[|$)", content)
        return json.loads(state_text), [parse_event(event) for event in events]
    if content.startswith("DECISION_CLOCK_GRID"):
        lines = content.splitlines()
        state = json.loads(next(line[8:] for line in lines if line.startswith("INITIAL=")))
        begin = lines.index("ROWS_BEGIN") + 1
        end = lines.index("ROWS_END")
        events = [parse_event(line.split("::", 1)[1]) for line in lines[begin:end] if line.startswith("GRID_ROW::")]
        return state, events
    if content.startswith("MULTI_SYSTEM_JOURNAL<"):
        state_text = content.split(" STATE::", 1)[1].split(" SUBMISSIONS::", 1)[0]
        queue = content.split(" SUBMISSIONS::", 1)[1].split(" CLOSE_AT::", 1)[0]
        return json.loads(state_text), [parse_event(event) for event in queue.split(" || ")]
    if content.startswith("QUEUE CONTROL SHEET"):
        lines = content.splitlines()
        state = json.loads(next(line.split(": ", 1)[1] for line in lines if line.startswith("Initial typed state: ")))
        events = [
            parse_event(line[len("CONTROL_LINE["):-1])
            for line in lines
            if line.startswith("CONTROL_LINE[") and line.endswith("]")
        ]
        return state, events
    if content.startswith("Cross-format register"):
        state_text = content.split("Begin from typed state ", 1)[1].split(". Entries are submitted", 1)[0]
        events = re.findall(r"REGISTER_ENTRY\[(.*?)\](?= REGISTER_ENTRY\[|$)", content)
        return json.loads(state_text), [parse_event(event) for event in events]
    if content.startswith("CONTROL_BRIEF"):
        lines = content.splitlines()
        state = json.loads(next(line[6:] for line in lines if line.startswith("STATE=")))
        begin = lines.index("QUEUE_BEGIN") + 1
        end = lines.index("QUEUE_END")
        events = [parse_event(line.split("::", 1)[1]) for line in lines[begin:end] if line.startswith("CONTROL_EVENT::")]
        return state, events
    if content.startswith("TIMELINE_LEDGER<"):
        state_text = content.split(" INITIAL::", 1)[1].split(" SUBMITTED::", 1)[0]
        queue = content.split(" SUBMITTED::", 1)[1].rsplit(" DECIDE_AT::", 1)[0]
        return json.loads(state_text), [parse_event(event) for event in queue.split(" || ")]
    if content.startswith("DOMAIN="):
        lines = content.splitlines()
        state = json.loads(next(line[6:] for line in lines if line.startswith("STATE=")))
        begin = lines.index("EVENT_QUEUE_BEGIN") + 1
        end = lines.index("EVENT_QUEUE_END")
        return state, [parse_event(line) for line in lines[begin:end]]
    if content.startswith("Operations memorandum"):
        state_match = re.search(r"The typed institutional state is (\{.*?\})\. The submitted queue", content)
        if not state_match:
            raise ValueError("operations memo state missing")
        events = re.findall(r"EVENT\[(.*?)\](?= EVENT\[|$)", content)
        return json.loads(state_match.group(1)), [parse_event(event) for event in events]
    if content.startswith("DOCKET<"):
        lines = content.splitlines()
        state = json.loads(next(line.split("::", 1)[1] for line in lines if line.startswith("INITIAL_RECORD::")))
        queue = next(line.split("::", 1)[1] for line in lines if line.startswith("SCHEDULED_ENTRIES::"))
        return state, [parse_event(event) for event in queue.split(" || ")]
    if content.startswith("Review memorandum"):
        state_text = content.split(" typed initial record ", 1)[1].split(" at disposition time ", 1)[0]
        events = re.findall(r"REVIEW_ENTRY\[(.*?)\](?= REVIEW_ENTRY\[|$)", content)
        return json.loads(state_text), [parse_event(event) for event in events]
    raise ValueError("unknown EventNet observation renderer")