"""OpenAI tool definitions and dispatch for the secretary agent.

Each entry maps tool name -> (JSONSchema spec, async callable).
Callables always return a string the model can read.
"""
from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone as _tz
from zoneinfo import ZoneInfo

from handlers import todo, reminder, memory, calendar, curriculum
from handlers.news import (
    fetch_and_summarize,
    get_recent_digests,
    update_preferences,
)
from handlers.search import web_search

TZ = ZoneInfo("America/New_York")


def _parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


# ---------------- todo ----------------

async def _t_add_todo(text: str, priority: str = "normal", tags: list[str] | None = None,
                     due_date: str | None = None, recurrence_rule: str | None = None,
                     recurrence_interval: int = 1) -> str:
    r = todo.add_todo(text, priority, tags or [], due_date, recurrence_rule, recurrence_interval)
    parts = [f"Added '{r['text']}'"]
    if priority != "normal":
        parts.append(f"({priority})")
    if r.get("tags"):
        parts.append(" ".join(f"#{t}" for t in r["tags"].split(",") if t))
    if r.get("due_date"):
        parts.append(f"(due {r['due_date']})")
    if r.get("recurrence_rule"):
        parts.append(f"(repeats {r['recurrence_rule']})")
    return " ".join(parts)


async def _t_list_todos(include_done: bool = False) -> str:
    rows = todo.list_todos(include_done=include_done)
    return todo.format_todo_list(rows)


async def _t_complete_todos(positions: list[int]) -> str:
    done = 0
    missing = []
    already = []
    next_dues = []
    for p in positions:
        r = todo.complete_todo(int(p))
        if not r["success"]:
            missing.append(p)
        elif r.get("already_done"):
            already.append(p)
        else:
            done += 1
            if r.get("next_due"):
                next_dues.append((p, r["next_due"]))
    parts = []
    if done:
        parts.append(f"Marked {done} done.")
    if already:
        parts.append(f"Already done: {already}.")
    if missing:
        parts.append(f"No task at: {missing}.")
    for p, d in next_dues:
        parts.append(f"Task {p} repeats — next {d.strftime('%b %d')}.")
    return " ".join(parts) or "Nothing changed."


async def _t_uncomplete_todos(positions: list[int]) -> str:
    ok = 0
    missing = []
    for p in positions:
        if todo.uncomplete_todo(int(p)):
            ok += 1
        else:
            missing.append(p)
    parts = []
    if ok:
        parts.append(f"Marked {ok} not done.")
    if missing:
        parts.append(f"No task at: {missing}.")
    return " ".join(parts) or "Nothing changed."


async def _t_delete_todos(positions: list[int]) -> str:
    deleted = 0
    missing = []
    for p in sorted([int(x) for x in positions], reverse=True):
        if todo.delete_todo(p):
            deleted += 1
        else:
            missing.append(p)
    parts = []
    if deleted:
        parts.append(f"Deleted {deleted}.")
    if missing:
        parts.append(f"No task at: {missing}.")
    return " ".join(parts) or "Nothing deleted."


async def _t_clear_all_todos() -> str:
    return f"Cleared {todo.clear_all_todos()} pending task(s)."


async def _t_clear_completed_todos() -> str:
    return f"Cleared {todo.clear_completed_todos()} completed task(s)."


async def _t_complete_all_todos() -> str:
    return f"Marked {todo.complete_all_todos()} task(s) done."


async def _t_rename_todo(position: int, new_text: str) -> str:
    return f"Renamed task {position} to '{new_text}'." if todo.rename_todo(int(position), new_text) else f"No task at {position}."


async def _t_move_todo(from_position: int, to_position: int) -> str:
    rows = todo.list_todos(include_done=True)
    actual_to = min(int(to_position), len(rows))
    return "Moved." if todo.move_todo(int(from_position), actual_to) else "Couldn't move."


async def _t_set_priority(position: int, priority: str) -> str:
    return f"Priority of {position} set to {priority}." if todo.set_priority(int(position), priority) else "Failed."


async def _t_set_tags(position: int, tags: list[str]) -> str:
    return "Tags set." if todo.set_tags(int(position), tags) else "Failed."


async def _t_list_by_tag(tag: str) -> str:
    rows = todo.list_by_tag(tag)
    if not rows:
        return f"No tasks tagged #{tag.lstrip('#')}."
    return f"Tasks tagged #{tag.lstrip('#')}:\n" + todo.format_todo_list(rows)


async def _t_set_due_date(position: int, due_date: str | None) -> str:
    ok = todo.set_due_date(int(position), due_date)
    if not ok:
        return "Failed."
    return f"Due date set to {due_date}." if due_date else "Due date cleared."


async def _t_set_recurrence(position: int, recurrence_rule: str | None, recurrence_interval: int = 1) -> str:
    ok = todo.set_recurrence(int(position), recurrence_rule, recurrence_interval)
    if not ok:
        return "Failed."
    return f"Recurrence set to {recurrence_rule}." if recurrence_rule else "Recurrence cleared."


# ---------------- reminders ----------------

async def _t_add_reminder(text: str, remind_at: str) -> str:
    dt = _parse_dt(remind_at)
    r = reminder.add_reminder(text, dt.astimezone(_tz.utc))
    return f"Reminder set: '{r['text']}' at {dt.strftime('%Y-%m-%d %H:%M %Z')}"


async def _t_list_reminders() -> str:
    return reminder.format_reminders(reminder.list_pending_reminders())


async def _t_snooze_reminder(id: int, minutes: int = 30) -> str:
    return f"Snoozed {minutes}m." if reminder.snooze_reminder(int(id), int(minutes)) else f"No reminder {id}."


# ---------------- memory ----------------

async def _t_store_memory(raw_input: str) -> str:
    r = await memory.store_memory(raw_input)
    return f"Stored: trigger on '{r['trigger_pattern']}' -> {r['action_type']}"


async def _t_list_memories() -> str:
    return memory.format_memories(memory.get_all_memories())


async def _t_delete_memory(id: int) -> str:
    return "Deleted." if memory.delete_memory(int(id)) else f"No memory {id}."


# ---------------- calendar ----------------

async def _t_list_events(days: int = 7) -> str:
    try:
        events = await calendar.list_events(days=int(days))
        return calendar.format_events(events)
    except Exception as e:
        return f"Calendar error: {e}"


async def _t_create_event(summary: str, start: str, end: str,
                          description: str | None = None, location: str | None = None) -> str:
    try:
        e = await calendar.create_event(summary=summary, start=start, end=end,
                                        description=description, location=location)
        dt = datetime.fromisoformat(e["start"]).astimezone(TZ)
        return f"Event created: '{e['summary']}' on {dt.strftime('%a %b %d at %I:%M %p')}."
    except Exception as ex:
        return f"Couldn't create event: {ex}"


async def _t_delete_event(id: str | None = None, query: str | None = None) -> str:
    try:
        if id:
            await calendar.delete_event(id)
            return "Event deleted."
        if query:
            events = await calendar.find_event(query)
            if not events:
                return f"No events matching '{query}'."
            if len(events) == 1:
                await calendar.delete_event(events[0]["id"])
                return f"Deleted '{events[0]['summary']}'."
            return "Multiple events match:\n" + calendar.format_events(events)
        return "Need id or query."
    except Exception as ex:
        return f"Couldn't delete: {ex}"


# ---------------- news ----------------

async def _t_get_news(category: str = "tech") -> str:
    return await fetch_and_summarize(category)


async def _t_news_recall(category: str = "tech", question: str = "") -> str:
    digests = get_recent_digests(category=category, limit=3)
    if not digests:
        return f"No past {category} digests."
    return "\n\n---\n\n".join(f"{d['created_at']}\n{d['digest']}" for d in digests)


async def _t_news_preferences(category: str = "tech", follow: str | None = None, skip: str | None = None) -> str:
    update_preferences(category=category, follow=follow, skip=skip)
    parts = []
    if follow:
        parts.append(f"following: {follow}")
    if skip:
        parts.append(f"skipping: {skip}")
    return f"{category} prefs updated — {', '.join(parts)}."


# ---------------- search ----------------

async def _t_web_search(query: str) -> str:
    return await web_search(query)


# ---------------- curriculum ----------------

async def _t_next_lesson() -> str:
    return await curriculum.deliver_next_lesson(mark_done=True)


async def _t_current_lesson() -> str:
    return await curriculum.deliver_current_lesson()


async def _t_lesson_status() -> str:
    return curriculum.get_status()


# ---------------- registry ----------------

def _tool(name: str, desc: str, params: dict, fn) -> dict:
    return {
        "spec": {
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": params,
            },
        },
        "fn": fn,
    }


REGISTRY: dict[str, dict] = {}


def _register(name, desc, params, fn):
    REGISTRY[name] = _tool(name, desc, params, fn)


_PRIORITY = ["high", "medium", "normal", "low"]
_RECUR = ["daily", "weekly", "monthly", "weekdays"]

_register("add_todo", "Add a new task to the todo list.",
    {"type": "object", "properties": {
        "text": {"type": "string", "description": "Task description, with command verbs stripped."},
        "priority": {"type": "string", "enum": _PRIORITY},
        "tags": {"type": "array", "items": {"type": "string"}},
        "due_date": {"type": ["string", "null"], "description": "YYYY-MM-DD or null"},
        "recurrence_rule": {"type": ["string", "null"], "enum": _RECUR + [None]},
        "recurrence_interval": {"type": "integer", "default": 1},
    }, "required": ["text"]}, _t_add_todo)

_register("list_todos", "List todo tasks. Set include_done=true to also show completed.",
    {"type": "object", "properties": {"include_done": {"type": "boolean", "default": False}}}, _t_list_todos)

_register("complete_todos", "Mark one or more tasks done by position.",
    {"type": "object", "properties": {"positions": {"type": "array", "items": {"type": "integer"}}},
     "required": ["positions"]}, _t_complete_todos)

_register("uncomplete_todos", "Mark one or more completed tasks as not done.",
    {"type": "object", "properties": {"positions": {"type": "array", "items": {"type": "integer"}}},
     "required": ["positions"]}, _t_uncomplete_todos)

_register("delete_todos", "Delete one or more tasks by position.",
    {"type": "object", "properties": {"positions": {"type": "array", "items": {"type": "integer"}}},
     "required": ["positions"]}, _t_delete_todos)

_register("clear_all_todos", "Delete ALL pending (not-done) tasks.",
    {"type": "object", "properties": {}}, _t_clear_all_todos)

_register("clear_completed_todos", "Delete all completed/done tasks.",
    {"type": "object", "properties": {}}, _t_clear_completed_todos)

_register("complete_all_todos", "Mark all pending tasks as done.",
    {"type": "object", "properties": {}}, _t_complete_all_todos)

_register("rename_todo", "Rename a task.",
    {"type": "object", "properties": {
        "position": {"type": "integer"}, "new_text": {"type": "string"}},
     "required": ["position", "new_text"]}, _t_rename_todo)

_register("move_todo", "Reorder a task. Use to_position=999 for bottom.",
    {"type": "object", "properties": {
        "from_position": {"type": "integer"}, "to_position": {"type": "integer"}},
     "required": ["from_position", "to_position"]}, _t_move_todo)

_register("set_priority", "Set priority on a task.",
    {"type": "object", "properties": {
        "position": {"type": "integer"}, "priority": {"type": "string", "enum": _PRIORITY}},
     "required": ["position", "priority"]}, _t_set_priority)

_register("set_tags", "Replace tags on a task.",
    {"type": "object", "properties": {
        "position": {"type": "integer"}, "tags": {"type": "array", "items": {"type": "string"}}},
     "required": ["position", "tags"]}, _t_set_tags)

_register("list_by_tag", "List tasks filtered by tag.",
    {"type": "object", "properties": {"tag": {"type": "string"}}, "required": ["tag"]}, _t_list_by_tag)

_register("set_due_date", "Set or clear (null) due date on a task.",
    {"type": "object", "properties": {
        "position": {"type": "integer"}, "due_date": {"type": ["string", "null"]}},
     "required": ["position"]}, _t_set_due_date)

_register("set_recurrence", "Set or clear (null rule) recurrence on a task.",
    {"type": "object", "properties": {
        "position": {"type": "integer"},
        "recurrence_rule": {"type": ["string", "null"], "enum": _RECUR + [None]},
        "recurrence_interval": {"type": "integer", "default": 1}},
     "required": ["position"]}, _t_set_recurrence)

_register("add_reminder", "Set a reminder. remind_at is ISO datetime; if no timezone, assume America/New_York.",
    {"type": "object", "properties": {
        "text": {"type": "string"}, "remind_at": {"type": "string"}},
     "required": ["text", "remind_at"]}, _t_add_reminder)

_register("list_reminders", "List pending reminders.",
    {"type": "object", "properties": {}}, _t_list_reminders)

_register("snooze_reminder", "Snooze a reminder by id.",
    {"type": "object", "properties": {
        "id": {"type": "integer"}, "minutes": {"type": "integer", "default": 30}},
     "required": ["id"]}, _t_snooze_reminder)

_register("store_memory",
    "Store a behavioral rule the user wants the secretary to remember (e.g. 'when I say X, do Y'). Pass the full raw user message.",
    {"type": "object", "properties": {"raw_input": {"type": "string"}}, "required": ["raw_input"]}, _t_store_memory)

_register("list_memories", "List stored behavioral memory rules.",
    {"type": "object", "properties": {}}, _t_list_memories)

_register("delete_memory", "Delete a memory rule by id.",
    {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}, _t_delete_memory)

_register("list_events", "List upcoming Google Calendar events.",
    {"type": "object", "properties": {"days": {"type": "integer", "default": 7}}}, _t_list_events)

_register("create_event", "Create a Google Calendar event. start/end are ISO datetimes.",
    {"type": "object", "properties": {
        "summary": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"},
        "description": {"type": ["string", "null"]}, "location": {"type": ["string", "null"]}},
     "required": ["summary", "start", "end"]}, _t_create_event)

_register("delete_event", "Delete a Google Calendar event by id, or by free-text query.",
    {"type": "object", "properties": {
        "id": {"type": ["string", "null"]}, "query": {"type": ["string", "null"]}}}, _t_delete_event)

_register("get_news", "Fetch and summarize the latest news in a category.",
    {"type": "object", "properties": {"category": {"type": "string", "enum": ["tech", "finance"]}}}, _t_get_news)

_register("news_recall", "Recall past news digests for a category.",
    {"type": "object", "properties": {
        "category": {"type": "string", "enum": ["tech", "finance"]},
        "question": {"type": "string"}}}, _t_news_recall)

_register("news_preferences", "Update follow/skip topics for a news category.",
    {"type": "object", "properties": {
        "category": {"type": "string", "enum": ["tech", "finance"]},
        "follow": {"type": ["string", "null"]}, "skip": {"type": ["string", "null"]}}}, _t_news_preferences)

_register("web_search", "Search the web and summarize the results.",
    {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, _t_web_search)

_register("next_lesson", "Deliver the next curriculum lesson.",
    {"type": "object", "properties": {}}, _t_next_lesson)

_register("current_lesson", "Re-deliver the current/last curriculum lesson.",
    {"type": "object", "properties": {}}, _t_current_lesson)

_register("lesson_status", "Show curriculum progress.",
    {"type": "object", "properties": {}}, _t_lesson_status)


def get_tool_specs() -> list[dict]:
    return [t["spec"] for t in REGISTRY.values()]


async def call_tool(name: str, arguments: str) -> str:
    if name not in REGISTRY:
        return json.dumps({"error": f"unknown tool '{name}'"})
    try:
        kwargs = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"bad arguments json: {e}"})
    fn = REGISTRY[name]["fn"]
    try:
        result = fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, str) else json.dumps(result, default=str)
    except TypeError as e:
        return json.dumps({"error": f"bad args for {name}: {e}"})
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"})
