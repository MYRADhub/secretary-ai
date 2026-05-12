import os
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TZ = ZoneInfo("America/New_York")
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "token.json")


def _get_service():
    creds = Credentials.from_authorized_user_file(os.path.abspath(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(os.path.abspath(TOKEN_PATH), "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def _parse_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime") or start.get("date", "")
    end_str = end.get("dateTime") or end.get("date", "")
    return {
        "id": event["id"],
        "summary": event.get("summary", "(no title)"),
        "start": start_str,
        "end": end_str,
        "location": event.get("location"),
        "description": event.get("description"),
    }


async def list_events(days: int = 7, max_results: int = 20) -> list[dict]:
    def _fetch():
        service = _get_service()
        now = datetime.now(TZ).isoformat()
        from datetime import timedelta
        until = (datetime.now(TZ) + timedelta(days=days)).isoformat()
        result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=until,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return [_parse_event(e) for e in result.get("items", [])]
    return await asyncio.to_thread(_fetch)


async def create_event(summary: str, start: str, end: str, description: str | None = None, location: str | None = None) -> dict:
    def _create():
        service = _get_service()
        body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "America/New_York"},
            "end": {"dateTime": end, "timeZone": "America/New_York"},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        event = service.events().insert(calendarId="primary", body=body).execute()
        return _parse_event(event)
    return await asyncio.to_thread(_create)


async def delete_event(event_id: str) -> bool:
    def _delete():
        service = _get_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return True
    return await asyncio.to_thread(_delete)


async def find_event(query: str) -> list[dict]:
    def _search():
        service = _get_service()
        result = service.events().list(
            calendarId="primary",
            q=query,
            maxResults=5,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        return [_parse_event(e) for e in result.get("items", [])]
    return await asyncio.to_thread(_search)


def format_events(events: list[dict]) -> str:
    if not events:
        return "No upcoming events."
    lines = []
    for e in events:
        start = e["start"]
        try:
            dt = datetime.fromisoformat(start)
            if dt.tzinfo:
                dt = dt.astimezone(TZ)
            start_fmt = dt.strftime("%a %b %d, %I:%M %p")
        except ValueError:
            start_fmt = start
        line = f"[{e['id'][:8]}] {e['summary']} — {start_fmt}"
        if e.get("location"):
            line += f" @ {e['location']}"
        lines.append(line)
    return "\n".join(lines)
