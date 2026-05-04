"""
Schabi API client for homework retrieval.

Handles authentication (cookie-based) and fetching homework/tasks/events
for a specific child (identified by username/password + schoolClass).

Supports the multi-child setup where each child has its own credentials
and schoolClass ID configured via environment variables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import httpx


@dataclass
class HomeworkItem:
    """A single homework task or event for a child."""

    day: str  # YYYY-MM-DD
    isEvent: bool
    task: str
    done: bool | None  # None for events; bool for tasks (True=done)


class SchabiAuthError(Exception):
    """Raised when authentication against Schabi fails."""


class SchabiClient:
    """HTTP client for the Schabi JSON API.

    Uses a persistent httpx.Client to maintain session cookies across
    requests. Login is performed lazily on first data request.
    """

    BASE_URL = "https://api.schabi.ch"

    def __init__(self, username: str, password: str, school_class: int) -> None:
        self.username = username
        self.password = password
        self.school_class = school_class
        self._client = httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._logged_in = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Authenticate and establish a session cookie."""
        auth_url = f"{self.BASE_URL}/api/auth/login"
        payload = {
            "UserName": self.username,
            "Password": self.password,
            "RememberMe": False,
            "device": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
            ),
            "app": False,
        }

        response = self._client.post(auth_url, json=payload)
        response.raise_for_status()

        # Schabi returns 200 even on failure in some cases; we rely on
        # subsequent calls failing if auth was bad. For robustness we
        # could inspect body, but cookie presence is what matters.
        self._logged_in = True

    def _ensure_logged_in(self) -> None:
        if not self._logged_in:
            self.login()

    # ------------------------------------------------------------------
    # Homework
    # ------------------------------------------------------------------

    def get_homework(self, for_date: str | None = None) -> list[HomeworkItem]:
        """Fetch homework and events for the given date (defaults to today).

        Returns a list of HomeworkItem. For regular tasks the ``done``
        flag reflects the pupil's completion status. Events have ``done=None``.
        """
        self._ensure_logged_in()

        if for_date is None:
            for_date = date.today().strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/api/homework/get"
        payload = {
            "date": for_date,
            "schoolClass": self.school_class,
            "view": "list",
        }

        response = self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        content = data.get("content", [])

        items: list[HomeworkItem] = []
        for day_block in content:
            day = str(day_block.get("day", ""))[:10]
            for task in day_block.get("tasks", []):
                assigned_to = task.get("assignedTo", [])
                done_pupil: bool | None = None
                if isinstance(assigned_to, list) and len(assigned_to) > 0:
                    done_pupil = bool(assigned_to[0].get("donePupil", False))

                task_name = task.get("task", "Unnamed Task")
                is_event = bool(task.get("event", False))

                if is_event:
                    items.append(
                        HomeworkItem(day=day, isEvent=True, task=task_name, done=None)
                    )
                else:
                    items.append(
                        HomeworkItem(
                            day=day, isEvent=False, task=task_name, done=done_pupil
                        )
                    )

        return items

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def __enter__(self) -> "SchabiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()
