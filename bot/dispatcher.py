import json
import re
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from llm.client import chat
from handlers import todo, reminder, memory
from handlers.news import get_recent_digests, update_preferences, fetch_and_summarize
from handlers.search import web_search
from handlers import calendar
from handlers import curriculum

TZ = ZoneInfo("America/New_York")
HISTORY_MAX = 100
_history: deque = deque(maxlen=HISTORY_MAX)

INTENT_SYSTEM_TEMPLATE = """You are an intent classifier for a personal secretary bot. Classify the user's message and extract clean parameters. Also check if any stored memory rules apply.

Intents:
- add_todo: adding a task. Extract ONLY the task text, strip command phrases like "add", "put", "to my list", etc. Extract tags, due date, and recurrence if mentioned.
  params: {{"text": "...", "priority": "high|medium|normal|low", "tags": ["tag1"], "due_date": "YYYY-MM-DD or null", "recurrence_rule": "daily|weekly|monthly|weekdays or null", "recurrence_interval": 1}}
- list_todos: show full task list with no filtering. params: {{"include_done": true/false}}
- filter_todos: user wants a filtered or sorted view. params: {{"query": "...", "include_done": true/false}}
- complete_todo: mark a task done. params: {{"position": <int or null>}}
- complete_all_todos: mark all tasks done
- delete_todo: delete one task. params: {{"position": <int>}}
- clear_all_todos: delete all pending tasks
- rename_todo: rename a task. params: {{"position": <int>, "new_text": "..."}}
- move_todo: reorder a task. params: {{"from_position": <int>, "to_position": <int>}}
  e.g. "move task 2 to top" to_position: 1; "move task 1 to bottom" to_position: 999
- set_priority: set task priority. params: {{"position": <int>, "priority": "high|medium|normal|low"}}
- set_tags: set or replace tags on a task. params: {{"position": <int>, "tags": ["tag1", "tag2"]}}
- list_by_tag: show tasks with a specific tag. params: {{"tag": "..."}}
- set_due_date: set or clear a due date on a task. params: {{"position": <int>, "due_date": "YYYY-MM-DD or null"}}
- set_recurrence: set or clear a recurrence rule on an existing task. params: {{"position": <int>, "recurrence_rule": "daily|weekly|monthly|weekdays or null", "recurrence_interval": 1}}
- add_reminder: set a reminder. params: {{"text": "...", "remind_at": "<ISO datetime>"}}
- list_reminders: list pending reminders
- snooze_reminder: snooze a reminder by ID. params: {{"id": <int>, "minutes": <int>}}
- store_memory: store a behavioral rule ("remember that...")
- list_memories: list stored memories
- delete_memory: delete a memory. params: {{"id": <int>}}
- get_news: user wants news now. params: {{"category": "tech|finance"}}
- news_recall: user asks about a past digest. params: {{"category": "tech|finance"}}
- news_preferences: user wants to change news topics. params: {{"category": "tech|finance", "follow": "...", "skip": "..."}}
- web_search: user wants to search the web or asks a factual question. params: {{"query": "..."}}
- list_events: list upcoming calendar events. params: {{"days": <int, default 7>}}
- create_event: add a calendar event. params: {{"summary": "...", "start": "<ISO datetime>", "end": "<ISO datetime>", "description": "...", "location": "..."}}
- delete_event: delete a calendar event by id. params: {{"id": "...", "query": "..."}} — use query if id unknown
- next_lesson: user wants the next lesson in the curriculum. no params.
- current_lesson: user wants to re-read or revisit the current/last lesson. no params.
- lesson_status: user wants to see their curriculum progress. no params.
- clear_history: reset conversation history
- general: anything else

Memory rules (check if any apply to this message):
{memory_rules}

Return JSON only: {{"intent": "<intent>", "params": {{}}, "matched_memory_id": <id or null>}}
Current datetime: """


def _get_memory_rules_text() -> str:
    memories = memory.get_all_memories()
    if not memories:
        return "None stored."
    return "\n".join(f"ID {m['id']}: {m['trigger_pattern']}" for m in memories)


async def parse_intent(message: str) -> tuple[dict, list[dict]]:
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    memory_rules_text = _get_memory_rules_text()
    system = INTENT_SYSTEM_TEMPLATE.format(memory_rules=memory_rules_text) + now

    messages = [{"role": "system", "content": system}]
    messages += list(_history)
    messages.append({"role": "user", "content": message})

    response = await chat(messages=messages)

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
        else:
            parsed = {"intent": "general", "params": {}, "matched_memory_id": None}

    matched_memory_id = parsed.pop("matched_memory_id", None)
    matched_memories = []
    if matched_memory_id:
        all_memories = memory.get_all_memories()
        matched_memories = [m for m in all_memories if m["id"] == matched_memory_id]

    return parsed, matched_memories


async def dispatch(message: str) -> str:
    parsed, matched_memories = await parse_intent(message)
    intent = parsed.get("intent", "general")
    params = parsed.get("params", {})

    if matched_memories:
        mem = matched_memories[0]
        action = mem["action_type"]
        mem_params = mem["action_params"]

        if action == "set_reminder":
            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?", message)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                offset = mem_params.get("offset_minutes", 0)
                remind_dt = datetime.now(TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
                remind_dt += timedelta(minutes=offset)
                label = mem_params.get("label", message)
                result = reminder.add_reminder(label, remind_dt)
                reply = f"Reminder set: '{result['text']}' at {remind_dt.strftime('%H:%M')} (from memory rule)"
                _history.append({"role": "user", "content": message})
                _history.append({"role": "assistant", "content": reply})
                return reply

        elif action == "add_todo":
            prefix = mem_params.get("prefix", "")
            result = todo.add_todo(f"{prefix}{message}")
            reply = f"Added: '{result['text']}'"
            _history.append({"role": "user", "content": message})
            _history.append({"role": "assistant", "content": reply})
            return reply

    if intent == "add_todo":
        text = params.get("text", message)
        priority = params.get("priority", "normal")
        tags = params.get("tags", [])
        due_date = params.get("due_date")
        recurrence_rule = params.get("recurrence_rule")
        recurrence_interval = params.get("recurrence_interval", 1)
        result = todo.add_todo(text, priority, tags, due_date, recurrence_rule, recurrence_interval)
        reply = f"Added: '{result['text']}'"
        if priority != "normal":
            reply += f" ({priority} priority)"
        if result["tags"]:
            reply += "  " + " ".join(f"#{t}" for t in result["tags"].split(",") if t)
        if result["due_date"]:
            reply += f"  (due {result['due_date']})"
        if result["recurrence_rule"]:
            reply += f"  (repeats {result['recurrence_rule']})"

    elif intent == "list_todos":
        include_done = params.get("include_done", False)
        todos = todo.list_todos(include_done=include_done)
        reply = todo.format_todo_list(todos)

    elif intent == "filter_todos":
        query = params.get("query", message)
        include_done = params.get("include_done", False)
        todos = todo.list_todos(include_done=include_done)
        if not todos:
            reply = "No tasks."
        else:
            tasks_text = "\n".join(
                f"{t['position']}. {'[done] ' if t['done'] else ''}[{t['priority']}] {t['text']}"
                for t in todos
            )
            reply = await chat(messages=[
                {"role": "system", "content": (
                    "You are a task list assistant. The user wants a filtered or sorted view of their tasks. "
                    "Apply the filter/sort and return ONLY the matching tasks as a clean numbered list. "
                    "Keep the original position numbers. If nothing matches, say so. Be concise."
                )},
                {"role": "user", "content": f"Tasks:\n{tasks_text}\n\nRequest: {query}"},
            ])

    elif intent == "complete_todo":
        position = params.get("position")
        if position:
            result = todo.complete_todo(int(position))
            if not result["success"]:
                reply = f"No task at position {position}."
            elif result["next_due"]:
                reply = f"Done. Next occurrence set for {result['next_due'].strftime('%b %d')}."
            else:
                reply = "Done."
        else:
            todos = todo.list_todos()
            reply = "Which task?\n" + todo.format_todo_list(todos)

    elif intent == "complete_all_todos":
        count = todo.complete_all_todos()
        reply = f"Marked {count} task(s) as done."

    elif intent == "delete_todo":
        position = params.get("position")
        if position:
            success = todo.delete_todo(int(position))
            reply = "Deleted." if success else f"No task at position {position}."
        else:
            todos = todo.list_todos()
            reply = "Which task?\n" + todo.format_todo_list(todos)

    elif intent == "clear_all_todos":
        count = todo.clear_all_todos()
        reply = f"Cleared {count} task(s)."

    elif intent == "rename_todo":
        position = params.get("position")
        new_text = params.get("new_text")
        if position and new_text:
            success = todo.rename_todo(int(position), new_text)
            reply = f"Renamed to '{new_text}'." if success else f"No task at position {position}."
        else:
            reply = "Tell me which task and what to rename it to."

    elif intent == "move_todo":
        from_pos = params.get("from_position")
        to_pos = params.get("to_position")
        if from_pos and to_pos:
            todos = todo.list_todos()
            actual_to = min(int(to_pos), len(todos))
            success = todo.move_todo(int(from_pos), actual_to)
            reply = "Moved." if success else "Couldn't move — check the positions."
        else:
            reply = "Tell me which task to move and where."

    elif intent == "set_priority":
        position = params.get("position")
        priority = params.get("priority", "normal")
        if position:
            success = todo.set_priority(int(position), priority)
            reply = f"Priority set to {priority}." if success else f"No task at position {position}."
        else:
            reply = "Which task should I set priority on?"

    elif intent == "set_tags":
        position = params.get("position")
        tags = params.get("tags", [])
        if position and tags:
            success = todo.set_tags(int(position), tags)
            tag_str = " ".join(f"#{t}" for t in tags)
            reply = f"Tags set: {tag_str}." if success else f"No task at position {position}."
        else:
            reply = "Tell me which task and what tags to set."

    elif intent == "list_by_tag":
        tag = params.get("tag", "")
        if tag:
            todos = todo.list_by_tag(tag)
            reply = f"Tasks tagged #{tag.lstrip('#')}:\n" + todo.format_todo_list(todos) if todos else f"No tasks tagged #{tag.lstrip('#')}."
        else:
            reply = "Which tag should I filter by?"

    elif intent == "set_due_date":
        position = params.get("position")
        due_date = params.get("due_date")
        if position:
            success = todo.set_due_date(int(position), due_date)
            if success:
                reply = f"Due date set to {due_date}." if due_date else "Due date cleared."
            else:
                reply = f"No task at position {position}."
        else:
            reply = "Which task should I set a due date on?"

    elif intent == "set_recurrence":
        position = params.get("position")
        rule = params.get("recurrence_rule")
        interval = params.get("recurrence_interval", 1)
        if position:
            success = todo.set_recurrence(int(position), rule, interval)
            if success:
                reply = f"Recurrence set to {rule}." if rule else "Recurrence cleared."
            else:
                reply = f"No task at position {position} or invalid rule."
        else:
            reply = "Which task should I set recurrence on?"

    elif intent == "add_reminder":
        text = params.get("text", message)
        remind_at_str = params.get("remind_at")
        if remind_at_str:
            try:
                remind_dt = datetime.fromisoformat(remind_at_str)
                result = reminder.add_reminder(text, remind_dt)
                reply = f"Reminder set: '{result['text']}' at {remind_dt.strftime('%Y-%m-%d %H:%M')}"
            except ValueError:
                reply = "Couldn't parse that time. Try 'remind me at 3pm tomorrow to call John'."
        else:
            reply = "When should I remind you?"

    elif intent == "list_reminders":
        reminders = reminder.list_pending_reminders()
        reply = reminder.format_reminders(reminders)

    elif intent == "snooze_reminder":
        reminder_id = params.get("id")
        minutes = params.get("minutes", 30)
        if reminder_id:
            success = reminder.snooze_reminder(int(reminder_id), int(minutes))
            if success:
                reply = f"Snoozed for {minutes} minute(s)."
            else:
                reply = f"No reminder with id {reminder_id}."
        else:
            reminders = reminder.list_pending_reminders()
            reply = "Which reminder id?\n" + reminder.format_reminders(reminders)

    elif intent == "store_memory":
        result = await memory.store_memory(message)
        reply = f"Stored: trigger on '{result['trigger_pattern']}' → {result['action_type']}"

    elif intent == "list_memories":
        memories = memory.get_all_memories()
        reply = memory.format_memories(memories)

    elif intent == "delete_memory":
        mem_id = params.get("id")
        if mem_id:
            success = memory.delete_memory(int(mem_id))
            reply = "Deleted." if success else f"No memory with id {mem_id}."
        else:
            reply = "Which memory id?"

    elif intent == "get_news":
        category = params.get("category", "tech")
        reply = await fetch_and_summarize(category)

    elif intent == "news_recall":
        category = params.get("category", "tech")
        digests = get_recent_digests(category=category, limit=3)
        if not digests:
            reply = f"No past {category} digests found."
        else:
            combined = "\n\n---\n\n".join(
                f"{d['created_at']}\n{d['digest']}" for d in digests
            )
            reply = await chat(messages=[
                {"role": "system", "content": "You are a helpful secretary. Answer the user's question using the past news digests below. Be concise."},
                {"role": "user", "content": f"Past digests:\n\n{combined}\n\nQuestion: {message}"},
            ])

    elif intent == "news_preferences":
        category = params.get("category", "tech")
        follow = params.get("follow")
        skip = params.get("skip")
        update_preferences(category=category, follow=follow, skip=skip)
        parts = []
        if follow:
            parts.append(f"following: {follow}")
        if skip:
            parts.append(f"skipping: {skip}")
        reply = f"{category.capitalize()} news preferences updated — {', '.join(parts)}."

    elif intent == "web_search":
        query = params.get("query", message)
        reply = await web_search(query)

    elif intent == "list_events":
        days = params.get("days", 7)
        try:
            events = await calendar.list_events(days=int(days))
            reply = calendar.format_events(events)
        except Exception as e:
            reply = f"Couldn't fetch calendar: {e}"

    elif intent == "create_event":
        summary = params.get("summary")
        start = params.get("start")
        end = params.get("end")
        if summary and start and end:
            try:
                event = await calendar.create_event(
                    summary=summary,
                    start=start,
                    end=end,
                    description=params.get("description"),
                    location=params.get("location"),
                )
                dt = datetime.fromisoformat(event["start"]).astimezone(TZ)
                reply = f"Event created: '{event['summary']}' on {dt.strftime('%a %b %d at %I:%M %p')}."
            except Exception as e:
                reply = f"Couldn't create event: {e}"
        else:
            reply = "Need a title, start time, and end time."

    elif intent == "delete_event":
        event_id = params.get("id")
        query = params.get("query")
        if event_id:
            try:
                await calendar.delete_event(event_id)
                reply = "Event deleted."
            except Exception as e:
                reply = f"Couldn't delete event: {e}"
        elif query:
            try:
                events = await calendar.find_event(query)
                if not events:
                    reply = f"No events found matching '{query}'."
                elif len(events) == 1:
                    await calendar.delete_event(events[0]["id"])
                    reply = f"Deleted '{events[0]['summary']}'."
                else:
                    reply = "Found multiple events — which one?\n" + calendar.format_events(events)
            except Exception as e:
                reply = f"Couldn't delete event: {e}"
        else:
            reply = "Which event should I delete?"

    elif intent == "next_lesson":
        reply = await curriculum.deliver_next_lesson(mark_done=True)

    elif intent == "current_lesson":
        reply = await curriculum.deliver_current_lesson()

    elif intent == "lesson_status":
        reply = curriculum.get_status()

    elif intent == "clear_history":
        _history.clear()
        reply = "Conversation history cleared. Fresh start."

    else:
        system = "You are a helpful personal secretary. Be concise and direct."
        messages = [{"role": "system", "content": system}]
        messages += list(_history)
        messages.append({"role": "user", "content": message})
        reply = await chat(messages=messages)

    _history.append({"role": "user", "content": message})
    _history.append({"role": "assistant", "content": reply})

    return reply
