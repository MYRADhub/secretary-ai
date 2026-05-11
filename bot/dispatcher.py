import json
import re
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from llm.client import chat

TZ = ZoneInfo("America/New_York")
from handlers import todo, reminder, memory
from handlers.news import get_recent_digests, update_preferences, fetch_and_summarize

HISTORY_MAX = 20
_history: deque = deque(maxlen=HISTORY_MAX)

INTENT_SYSTEM = """You are an intent classifier for a personal secretary bot. Classify the user's message and extract clean parameters.

Intents:
- add_todo: adding a task. Extract ONLY the task text, strip command phrases like "add", "put", "to my list", etc. Extract any tags (words starting with # or natural groupings like "for work", "personal").
  params: {"text": "...", "priority": "high|medium|normal|low", "tags": ["tag1", "tag2"]}
- list_todos: show full task list with no filtering. params: {"include_done": true/false} — true if user says "show all", "everything", "including done"
- filter_todos: user wants a filtered or sorted view — by keyword, person, priority, date, category, etc. params: {"query": "<the filter/sort description>", "include_done": true/false}
- complete_todo: mark a task done. params: {"position": <int or null>}
- complete_all_todos: mark all tasks done
- delete_todo: delete one task. params: {"position": <int>}
- clear_all_todos: delete all pending tasks
- rename_todo: rename a task. params: {"position": <int>, "new_text": "..."}
- move_todo: reorder a task. params: {"from_position": <int>, "to_position": <int>}
  e.g. "move task 2 to top" → to_position: 1; "move task 1 to bottom" → to_position: 999
- set_priority: set task priority. params: {"position": <int>, "priority": "high|medium|normal|low"}
- set_tags: set or replace tags on a task. params: {"position": <int>, "tags": ["tag1", "tag2"]}
- list_by_tag: show tasks with a specific tag. params: {"tag": "..."}
- add_reminder: set a reminder. params: {"text": "...", "remind_at": "<ISO datetime>"}
- list_reminders: list pending reminders
- store_memory: store a behavioral rule ("remember that...")
- list_memories: list stored memories
- delete_memory: delete a memory. params: {"id": <int>}
- get_news: user wants news now. params: {"category": "tech|finance"} — default "tech" unless user says "finance", "market", "stocks", "economy", etc.
- news_recall: user asks about a past digest. params: {"category": "tech|finance"} — infer from context, default "tech"
- news_preferences: user wants to change what news topics to follow or skip. params: {"category": "tech|finance", "follow": "...", "skip": "..."} — category default "tech", include only what was mentioned
- clear_history: user wants to reset/forget conversation history. Triggered by "forget this", "clear history", "start fresh", "new conversation", "ignore what we said", etc.
- general: anything else

Return JSON only: {"intent": "<intent>", "params": {}}
Current datetime: """


async def parse_intent(message: str) -> dict:
    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    system = INTENT_SYSTEM + now

    messages = [{"role": "system", "content": system}]
    messages += list(_history)
    messages.append({"role": "user", "content": message})

    response = await chat(messages=messages)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"intent": "general", "params": {}}


async def dispatch(message: str) -> str:
    matched_memories = await memory.match_memories(message)
    if matched_memories:
        mem = matched_memories[0]
        action = mem["action_type"]
        params = mem["action_params"]

        if action == "set_reminder":
            time_match = re.search(r"(\d{1,2})(?::(\d{2}))?", message)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                offset = params.get("offset_minutes", 0)
                remind_dt = datetime.now(TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
                remind_dt += timedelta(minutes=offset)
                label = params.get("label", message)
                result = reminder.add_reminder(label, remind_dt)
                return f"Reminder set: '{result['text']}' at {remind_dt.strftime('%H:%M')} (from memory rule)"

        elif action == "add_todo":
            prefix = params.get("prefix", "")
            result = todo.add_todo(f"{prefix}{message}")
            return f"Added: '{result['text']}'"

    parsed = await parse_intent(message)
    intent = parsed.get("intent", "general")
    params = parsed.get("params", {})

    if intent == "add_todo":
        text = params.get("text", message)
        priority = params.get("priority", "normal")
        tags = params.get("tags", [])
        result = todo.add_todo(text, priority, tags)
        reply = f"Added: '{result['text']}'"
        if priority != "normal":
            reply += f" ({priority} priority)"
        if result["tags"]:
            reply += "  " + " ".join(f"#{t}" for t in result["tags"].split(",") if t)

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
            success = todo.complete_todo(int(position))
            reply = "Done." if success else f"No task at position {position}."
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
