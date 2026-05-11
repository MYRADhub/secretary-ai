import json
import re
from collections import deque
from datetime import datetime, timedelta
from llm.client import chat
from handlers import todo, reminder, memory

HISTORY_MAX = 20
_history: deque = deque(maxlen=HISTORY_MAX)

INTENT_SYSTEM = """You are an intent classifier for a personal secretary bot. Classify the user's message and extract clean parameters.

Intents:
- add_todo: adding a task. Extract ONLY the task text, strip command phrases like "add", "put", "to my list", etc.
  params: {"text": "...", "priority": "high|medium|normal|low"}
- list_todos: show task list. params: {"include_done": true/false} — true if user says "show all", "everything", "including done"
- complete_todo: mark a task done. params: {"position": <int or null>}
- complete_all_todos: mark all tasks done
- delete_todo: delete one task. params: {"position": <int>}
- clear_all_todos: delete all pending tasks
- rename_todo: rename a task. params: {"position": <int>, "new_text": "..."}
- move_todo: reorder a task. params: {"from_position": <int>, "to_position": <int>}
  e.g. "move task 2 to top" → to_position: 1; "move task 1 to bottom" → to_position: 999
- set_priority: set task priority. params: {"position": <int>, "priority": "high|medium|normal|low"}
- add_reminder: set a reminder. params: {"text": "...", "remind_at": "<ISO datetime>"}
- list_reminders: list pending reminders
- store_memory: store a behavioral rule ("remember that...")
- list_memories: list stored memories
- delete_memory: delete a memory. params: {"id": <int>}
- get_news: user wants tech news
- clear_history: user wants to reset/forget conversation history. Triggered by "forget this", "clear history", "start fresh", "new conversation", "ignore what we said", etc.
- general: anything else

Return JSON only: {"intent": "<intent>", "params": {}}
Current datetime: """


async def parse_intent(message: str) -> dict:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
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


async def dispatch(message: str, send_news_fn=None) -> str:
    matched_memories = memory.match_memories(message)
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
                remind_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
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
        result = todo.add_todo(text, priority)
        reply = f"Added: '{result['text']}'"
        if priority != "normal":
            reply += f" ({priority} priority)"

    elif intent == "list_todos":
        include_done = params.get("include_done", False)
        todos = todo.list_todos(include_done=include_done)
        reply = todo.format_todo_list(todos)

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
        reply = await send_news_fn() if send_news_fn else "News unavailable."

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
