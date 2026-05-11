import json
import re
from storage.db import get_conn
from llm.client import chat


EXTRACT_SYSTEM = """You are a memory extraction engine. The user wants to store a behavioral rule.
Extract the rule into structured JSON with these fields:
- trigger_pattern: a regex or keyword phrase that will match future user messages
- action_type: one of "set_reminder", "add_todo", "custom_reply", "forward_to_llm"
- action_params: a dict with parameters relevant to the action

Examples:
User: "remember that when i say meeting with mark at 10 you set a reminder at 9:45"
Output: {"trigger_pattern": "meeting with mark at (\\d+)", "action_type": "set_reminder", "action_params": {"offset_minutes": -15, "label": "meeting with Mark"}}

User: "remember that groceries always go into a todo"
Output: {"trigger_pattern": "groceries", "action_type": "add_todo", "action_params": {"prefix": "Buy: "}}

Return ONLY valid JSON, no explanation."""


async def store_memory(raw_input: str) -> dict:
    response = await chat(
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": raw_input},
        ]
    )

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM returned non-JSON memory: {response}")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories (raw_input, trigger_pattern, action_type, action_params) VALUES (?, ?, ?, ?)",
        (
            raw_input,
            parsed["trigger_pattern"],
            parsed["action_type"],
            json.dumps(parsed["action_params"]),
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()

    return {"id": row_id, **parsed}


def get_all_memories() -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, raw_input, trigger_pattern, action_type, action_params FROM memories")
    rows = []
    for r in cur.fetchall():
        row = dict(r)
        row["action_params"] = json.loads(row["action_params"])
        rows.append(row)
    conn.close()
    return rows


def match_memories(message: str) -> list[dict]:
    memories = get_all_memories()
    matched = []
    for mem in memories:
        try:
            if re.search(mem["trigger_pattern"], message, re.IGNORECASE):
                matched.append(mem)
        except re.error:
            if mem["trigger_pattern"].lower() in message.lower():
                matched.append(mem)
    return matched


def delete_memory(memory_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def format_memories(memories: list[dict]) -> str:
    if not memories:
        return "No stored memories."
    lines = []
    for m in memories:
        lines.append(f"[{m['id']}] {m['raw_input']}")
    return "\n".join(lines)
