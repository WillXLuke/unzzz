"""Integration tests: real HTTP server, real SQLite, audio disabled."""

from __future__ import annotations

import http.cookiejar
import json
import shutil
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from unzzz.audio import build_beep
from unzzz.auth import Auth
from unzzz.db import Store
from unzzz.engine import Engine
from unzzz.web import App

PASSWORD = "correct-horse-battery"


class Client:
    def __init__(self, base: str) -> None:
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(self, method: str, path: str, body=None, csrf: bool = True, headers=None):
        data = None if body is None else json.dumps(body).encode()
        hdrs = {"Accept": "application/json"}
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        if csrf and method != "GET":
            hdrs["X-Unzzz-Csrf"] = "1"
        hdrs.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, headers=hdrs, method=method)
        try:
            resp = self.opener.open(req, timeout=8)
            status, raw = resp.status, resp.read()
            resp_headers = dict(resp.headers)
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
            resp_headers = dict(exc.headers)
            exc.close()
        try:
            payload = json.loads(raw) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = raw.decode("utf-8", "replace")
        return status, payload, resp_headers

    def request_bytes(self, method: str, path: str, data: bytes | None = None,
                      content_type: str | None = None, csrf: bool = True, headers=None):
        hdrs = {"Accept": "application/json"}
        if content_type:
            hdrs["Content-Type"] = content_type
        if csrf and method != "GET":
            hdrs["X-Unzzz-Csrf"] = "1"
        hdrs.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, headers=hdrs, method=method)
        try:
            resp = self.opener.open(req, timeout=8)
            return resp.status, resp.read(), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            body = exc.read()
            headers = dict(exc.headers)
            exc.close()
            return exc.code, body, headers


class ServerFixture:
    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-test-"))
        self.store = Store(self.tmp / "test.sqlite3")
        self.auth = Auth(self.store)
        self.engine = Engine(self.store, self.tmp, audio_command="none")
        self.app = App(self.store, self.engine, self.auth, self.tmp)
        self.httpd = self.app.make_server("127.0.0.1", 0)
        self.port = self.httpd.server_address[1]
        self.engine.start()
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True
        )
        self.thread.start()
        self.client = Client(f"http://127.0.0.1:{self.port}")

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.engine.stop()
        self.store.close()
        self.thread.join(timeout=3)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers -------------------------------------------------------------
    def setup_admin(self) -> None:
        status, data, _ = self.client.request(
            "POST", "/api/setup", {"password": PASSWORD}
        )
        assert status == 200, (status, data)

    def add_user(self, name: str) -> dict:
        status, data, _ = self.client.request("POST", "/api/users", {"name": name})
        assert status == 201, (status, data)
        return data["user"]

    def create_alarm(self, **over) -> dict:
        payload = {
            "label": "Wake up",
            "time": "07:30",
            "days": [1, 2, 3, 4, 5],
            "once_date": None,
            "enabled": True,
            "mode": "standard",
            "difficulty": "normal",
            "snooze_minutes": 9,
            "max_snoozes": 2,
            "max_ring_minutes": 15,
        }
        payload.update(over)
        status, data, _ = self.client.request("POST", "/api/alarms", payload)
        assert status == 201, (status, data)
        return data["alarm"]

    def state(self) -> dict:
        status, data, _ = self.client.request("GET", "/api/state")
        assert status == 200, (status, data)
        return data

    def ring(self, alarm_id: int) -> dict:
        status, data, _ = self.client.request(
            "POST", f"/api/alarms/{alarm_id}/ring", {}
        )
        assert status == 201, (status, data)
        return data["event"]

    def solve(self, token: str) -> dict:
        status, data, _ = self.client.request("GET", f"/api/s/{token}")
        assert status == 200, (status, data)
        question = data["challenge"]["question"]
        expression = question.replace("×", "*").replace("−", "-")
        answer = int(eval(expression, {"__builtins__": {}}, {}))
        return self.answer(token, str(answer))

    def answer(self, token: str, value: str) -> dict:
        status, data, _ = self.client.request(
            "POST", f"/api/s/{token}/answer", {"answer": value}
        )
        assert status == 200, (status, data)
        return data

    def add_question(self, question: str, answer: str,
                     kind: str = "text", options=None) -> dict:
        status, data, _ = self.client.request(
            "POST", "/api/questions",
            {"question": question, "answer": answer, "kind": kind,
             "options": options or []},
        )
        assert status == 201, (status, data)
        return data["question"]

    def add_calendar(self, name: str, csv_text: str) -> dict:
        status, data, _ = self.client.request(
            "POST", "/api/calendars", {"name": name, "csv": csv_text}
        )
        assert status == 201, (status, data)
        return data["calendar"]


class ApiBase(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = ServerFixture()

    def tearDown(self) -> None:
        self.fx.close()


class AuthTests(ApiBase):
    def test_setup_login_csrf_and_logout(self) -> None:
        status, data, _ = self.fx.client.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertTrue(data["needs_setup"])

        status, _data, _ = self.fx.client.request(
            "POST", "/api/alarms", {"label": "x", "time": "07:30", "days": [1]}
        )
        self.assertEqual(status, 401)

        status, _data, _ = self.fx.client.request(
            "POST", "/api/setup", {"password": "short"}
        )
        self.assertEqual(status, 400)

        self.fx.setup_admin()
        state = self.fx.state()
        self.assertTrue(state["authenticated"])
        self.assertFalse(state["needs_setup"])

        status, _data, _ = self.fx.client.request(
            "POST", "/api/alarms", {"label": "x"}, csrf=False
        )
        self.assertEqual(status, 403)

        status, _data, _ = self.fx.client.request(
            "POST",
            "/api/alarms",
            {"label": "x"},
            headers={"Origin": "http://evil.example"},
        )
        self.assertEqual(status, 403)

        status, _data, _ = self.fx.client.request("POST", "/api/logout", {})
        self.assertEqual(status, 200)
        status, _data, _ = self.fx.client.request("GET", "/api/state")
        self.assertEqual(status, 401)

        status, _data, _ = self.fx.client.request(
            "POST", "/api/login", {"password": "wrong"}
        )
        self.assertEqual(status, 401)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/login", {"password": PASSWORD}
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.fx.state()["authenticated"], True)

    def test_login_throttle(self) -> None:
        self.fx.setup_admin()
        self.fx.client.request("POST", "/api/logout", {})
        for _ in range(4):
            status, _data, _ = self.fx.client.request(
                "POST", "/api/login", {"password": "nope"}
            )
            self.assertEqual(status, 401)
        status, data, headers = self.fx.client.request(
            "POST", "/api/login", {"password": "nope"}
        )
        self.assertEqual(status, 429)
        self.assertIn("Retry-After", headers)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/login", {"password": PASSWORD}
        )
        self.assertEqual(status, 429)

    def test_password_change(self) -> None:
        self.fx.setup_admin()
        status, _data, _ = self.fx.client.request(
            "POST", "/api/password", {"current": "wrong", "new": "new-password-123"}
        )
        self.assertEqual(status, 403)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/password", {"current": PASSWORD, "new": "new-password-123"}
        )
        self.assertEqual(status, 200)
        # Existing session survives; other sessions would not.
        self.assertTrue(self.fx.state()["authenticated"])


class UserTests(ApiBase):
    def test_user_crud_and_alarm_selection_limit(self) -> None:
        self.fx.setup_admin()
        ada = self.fx.add_user("Ada")
        self.assertEqual(ada["name"], "Ada")
        status, data, _ = self.fx.client.request("POST", "/api/users", {"name": " ada "})
        self.assertEqual(status, 409)

        for name in ["Bob", "Cy", "Dee", "Eve", "Fay", "Gus"]:
            self.fx.add_user(name)

        state = self.fx.state()
        self.assertEqual(len(state["users"]), 7)
        self.assertEqual(state["limits"]["max_users"], 200)
        self.assertEqual(state["limits"]["max_alarm_users"], 6)

        status, data, _ = self.fx.client.request(
            "POST",
            "/api/alarms",
            {
                "label": "Too many",
                "time": "07:30",
                "days": [1, 2, 3, 4, 5],
                "mode": "challenge",
                "participants": list(range(1, 8)),
                "enabled": True,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("at most 6", data["error"])

        status, data, _ = self.fx.client.request(
            "PUT", f"/api/users/{ada['id']}", {"name": "Ada L."}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["name"], "Ada L.")
        status, data, _ = self.fx.client.request(
            "PUT", f"/api/users/{ada['id']}", {"active": False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["user"]["active"], 0)

        status, _data, _ = self.fx.client.request(
            "DELETE", f"/api/users/{ada['id']}"
        )
        self.assertEqual(status, 200)
        status, _data, _ = self.fx.client.request(
            "DELETE", f"/api/users/{ada['id']}"
        )
        self.assertEqual(status, 404)


class ChallengeFlowTests(ApiBase):
    def test_full_challenge_flow(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_user("Bob")
        self.fx.add_user("Cy")
        alarm = self.fx.create_alarm(mode="challenge", label="Morning")
        event = self.fx.ring(alarm["id"])
        self.assertEqual(event["state"], "ringing")
        self.assertEqual(event["total"], 3)

        state = self.fx.state()
        active = state["active_events"][0]
        self.assertEqual(active["mode"], "challenge")
        self.assertEqual(active["total"], 3)
        self.assertEqual(len(active["challenges"]), 3)
        for ch in active["challenges"]:
            self.assertTrue(ch["url"].startswith("http://127.0.0.1:"))
            self.assertIn("/s/", ch["url"])
            self.assertGreaterEqual(len(ch["token"]), 20)

        tokens = [ch["token"] for ch in active["challenges"]]
        # The page itself is public, capability-token protected.
        status, _data, headers = self.fx.client.request("GET", f"/s/{tokens[0]}")
        self.assertEqual(status, 200)
        self.assertIn("challenge.js", _data)
        self.assertIn("Content-Security-Policy", headers)

        # A challenge cannot be dismissed normally, and a user mid-answer
        # cannot be deleted out from under the event.
        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/stop", {"force": False}
        )
        self.assertEqual(status, 409)
        status, data, _ = self.fx.client.request(
            "DELETE", f"/api/users/{active['challenges'][0]['user_id']}"
        )
        self.assertEqual(status, 409)

        # Wrong answers are rejected and a fresh question is issued.
        status, data, _ = self.fx.client.request(
            "POST", f"/api/s/{tokens[0]}/answer", {"answer": "-999"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "wrong")
        self.assertEqual(data["answer"]["attempts"], 1)

        first = self.fx.solve(tokens[0])
        self.assertEqual(first["status"], "correct")
        self.assertFalse(first["all_done"])
        self.assertEqual(first["answer"]["answered_count"], 1)

        second = self.fx.solve(tokens[1])
        self.assertFalse(second["all_done"])
        self.assertEqual(second["answer"]["answered_count"], 2)

        third = self.fx.solve(tokens[2])
        self.assertTrue(third["all_done"])
        self.assertEqual(third["answer"]["state"], "completed")
        self.assertEqual(third["answer"]["stop_reason"], "answered by all users")

        deadline = time.time() + 3
        while self.fx.engine.rings and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(self.fx.engine.rings, {})

        state = self.fx.state()
        self.assertEqual(state["active_events"], [])
        self.assertEqual(state["history"][0]["state"], "completed")
        self.assertEqual(state["history"][0]["answered"], 3)

        # The shortlink becomes a read-only completion page.
        status, data, _ = self.fx.client.request("GET", f"/api/s/{tokens[0]}")
        self.assertEqual(status, 200)
        self.assertEqual(data["challenge"]["state"], "completed")
        self.assertIsNone(data["challenge"]["question"])

        status, data, _ = self.fx.client.request(
            "POST", f"/api/s/{tokens[0]}/answer", {"answer": "1"}
        )
        self.assertEqual(data["status"], "already")

        # Unknown tokens are 404.
        status, _data, _ = self.fx.client.request("GET", "/api/s/abcdefghijklmnop")
        self.assertEqual(status, 404)

    def test_emergency_stop_is_logged(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(mode="challenge")
        event = self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/stop", {"force": True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["event"]["state"], "stopped")
        state = self.fx.state()
        self.assertEqual(state["history"][0]["stop_reason"], "emergency stop by admin")

    def test_challenge_requires_active_user(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request(
            "POST",
            "/api/alarms",
            {
                "label": "Challenge",
                "time": "07:30",
                "days": [1, 2, 3, 4, 5],
                "mode": "challenge",
                "difficulty": "easy",
                "enabled": True,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("active user", data["error"])


class StandardAlarmTests(ApiBase):
    def test_standard_alarm_snooze_and_stop(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm(max_snoozes=1, snooze_minutes=1)
        event = self.fx.ring(alarm["id"])
        self.assertEqual(event["mode"], "standard")
        status, data, _ = self.fx.client.request(
            "DELETE", f"/api/alarms/{alarm['id']}"
        )
        self.assertEqual(status, 409)

        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/snooze", {}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["event"]["state"], "snoozed")
        self.assertEqual(data["event"]["snooze_count"], 1)

        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/snooze", {}
        )
        self.assertEqual(status, 409)

        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/stop", {"force": False}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["event"]["state"], "stopped")

        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarms/{alarm['id']}/ring", {}
        )
        self.assertEqual(status, 201)
        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarms/{alarm['id']}/ring", {}
        )
        self.assertEqual(status, 409)

    def test_snooze_refires_on_tick(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm(max_snoozes=1, snooze_minutes=1)
        event = self.fx.ring(alarm["id"])
        self.fx.client.request("POST", f"/api/events/{event['id']}/snooze", {})
        now = time.time()
        self.fx.store.set_event_state(
            event["id"], "snoozed", snooze_until=now - 2, snooze_count=1
        )
        self.fx.engine.tick(now)
        refreshed = self.fx.store.get_event(event["id"])
        self.assertEqual(refreshed["state"], "ringing")
        self.fx.engine.stop_event(event["id"], "test cleanup")

    def test_alarm_validation_errors(self) -> None:
        self.fx.setup_admin()
        for payload, needle in [
            ({"label": "x", "time": "7:30", "days": [1]}, "HH:MM"),
            ({"label": "x", "time": "07:30", "days": [1], "once_date": "2030-01-01"}, "not both"),
            ({"label": "x", "time": "07:30", "days": []}, "repeat days"),
            ({"label": "", "time": "07:30", "days": [1]}, "Label"),
        ]:
            status, data, _ = self.fx.client.request("POST", "/api/alarms", payload)
            self.assertEqual(status, 400, (payload, data))
            self.assertIn(needle, data["error"])


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="unzzz-sched-"))
        self.store = Store(self.tmp / "test.sqlite3")
        self.engine = Engine(self.store, self.tmp, audio_command="none")

    def tearDown(self) -> None:
        self.engine.stop()
        self.store.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_alarm(self, **over) -> dict:
        now = time.time()
        data = {
            "label": "Direct",
            "time": "07:30",
            "days_mask": 0b1111111,
            "once_date": None,
            "enabled": 1,
            "mode": "standard",
            "difficulty": "normal",
            "snooze_minutes": 9,
            "max_snoozes": 2,
            "max_ring_minutes": 15,
            "next_fire": now - 5,
        }
        data.update(over)
        return self.store.create_alarm(data)

    def test_due_alarm_fires_and_times_out(self) -> None:
        alarm = self.make_alarm()
        now = time.time()
        self.engine.tick(now)
        events = self.store.list_events(10)
        self.assertEqual(events[0]["state"], "ringing")
        self.assertEqual(events[0]["alarm_id"], alarm["id"])
        refreshed = self.store.get_alarm(alarm["id"])
        self.assertEqual(refreshed["enabled"], 1)  # daily alarms stay enabled
        self.assertGreater(refreshed["next_fire"], now)

        event_id = events[0]["id"]
        self.store.set_event_state(event_id, "ringing", ends_at=now - 1)
        self.engine.tick(now)
        self.assertEqual(self.store.get_event(event_id)["state"], "expired")

    def test_skip_next_occurrence(self) -> None:
        alarm = self.make_alarm()
        self.store.set_alarm_skip(alarm["id"], True)
        now = time.time()
        self.engine.tick(now)
        events = self.store.list_events(10)
        skipped = next(e for e in events if e["state"] == "skipped")
        self.assertEqual(skipped["alarm_id"], alarm["id"])
        self.assertIn("skipped", skipped["stop_reason"])
        self.assertEqual(self.store.get_alarm(alarm["id"])["skip_next"], 0)
        self.assertGreater(self.store.get_alarm(alarm["id"])["next_fire"], now)
        self.assertEqual(self.engine.rings, {})

    def test_missed_alarm_is_recorded_and_one_shot_disabled(self) -> None:
        now = time.time()
        alarm = self.make_alarm(
            days_mask=0, once_date="2026-10-25", next_fire=now - 1000
        )
        self.engine.tick(now)
        events = self.store.list_events(10)
        self.assertEqual(events[0]["state"], "missed")
        refreshed = self.store.get_alarm(alarm["id"])
        self.assertEqual(refreshed["enabled"], 0)
        self.assertIsNone(refreshed["next_fire"])

    def test_real_ticker_fires_a_due_alarm(self) -> None:
        alarm = self.make_alarm(next_fire=time.time() + 1.0)
        self.engine.start()
        found = None
        deadline = time.time() + 5
        while time.time() < deadline:
            events = self.store.list_events(10)
            if events and events[0]["state"] == "ringing":
                found = events[0]
                break
            time.sleep(0.1)
        self.assertIsNotNone(found, "ticker did not fire the alarm")
        self.assertEqual(found["alarm_id"], alarm["id"])
        self.engine.stop_event(found["id"], "test cleanup")

    def test_snooze_rearms_and_is_limited(self) -> None:
        alarm = self.make_alarm(max_snoozes=1)
        event = self.engine.fire_alarm(alarm["id"], manual=True)
        snoozed = self.engine.snooze_event(event["id"])
        self.assertEqual(snoozed["state"], "snoozed")
        with self.assertRaises(Exception):
            self.engine.snooze_event(event["id"])

        self.fx_now = time.time()
        self.store.set_event_state(
            event["id"], "snoozed", snooze_until=self.fx_now - 2, snooze_count=1
        )
        self.engine.tick(self.fx_now)
        again = self.store.get_event(event["id"])
        self.assertEqual(again["state"], "ringing")
        self.engine.stop_event(event["id"], "done")
        self.assertEqual(self.store.get_event(event["id"])["state"], "stopped")


class SettingsTests(ApiBase):
    def test_timezone_base_url_and_audio(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request(
            "POST", "/api/settings", {"timezone": "Mars/Olympus", "base_url": ""}
        )
        self.assertEqual(status, 400)
        status, data, _ = self.fx.client.request(
            "POST",
            "/api/settings",
            {"timezone": "Europe/Berlin", "base_url": "http://x/y"},
        )
        self.assertEqual(status, 400)

        status, data, _ = self.fx.client.request(
            "POST",
            "/api/settings",
            {"timezone": "Europe/Berlin", "base_url": "http://alarm.local:8888"},
        )
        self.assertEqual(status, 200)
        state = self.fx.state()
        self.assertEqual(state["timezone"], "Europe/Berlin")
        self.assertEqual(state["settings"]["effective_base_url"], "http://alarm.local:8888")

        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(mode="challenge")
        self.fx.ring(alarm["id"])
        state = self.fx.state()
        url = state["active_events"][0]["challenges"][0]["url"]
        self.assertTrue(url.startswith("http://alarm.local:8888/s/"))

        status, data, _ = self.fx.client.request("POST", "/api/audio/test", {})
        self.assertEqual(status, 400)
        self.assertIn("disabled", data["error"])

    def test_bad_json_and_methods(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request("GET", "/api/nope")
        self.assertEqual(status, 404)
        status, data, _ = self.fx.client.request(
            "POST", "/api/alarms", {"x": 1}, headers={"Content-Type": "text/plain"}
        )
        # Client always sets application/json after our header? It merges headers
        # last, so text/plain wins.
        self.assertEqual(status, 415)


if __name__ == "__main__":
    unittest.main()


class ParticipantTests(ApiBase):
    def test_only_selected_users_get_challenges(self) -> None:
        self.fx.setup_admin()
        for name in ["Ada", "Bob", "Cy", "Dee", "Eve", "Fay", "Gus"]:
            self.fx.add_user(name)
        alarm = self.fx.create_alarm(
            mode="challenge",
            participants=[2, 4, 5],
            completion_mode="all",
        )
        state = self.fx.state()
        stored = next(a for a in state["alarms"] if a["id"] == alarm["id"])
        self.assertEqual(stored["participant_ids"], [2, 4, 5])
        self.assertEqual([p["name"] for p in stored["participants"]], ["Bob", "Dee", "Eve"])
        self.assertTrue(stored["slug"])

        event = self.fx.ring(alarm["id"])
        self.assertEqual(event["total"], 3)
        state = self.fx.state()
        names = [c["user_name"] for c in state["active_events"][0]["challenges"]]
        self.assertEqual(names, ["Bob", "Dee", "Eve"])
        self.fx.client.request("POST", f"/api/events/{event['id']}/stop", {"force": True})


class CompletionTargetTests(ApiBase):
    def test_stops_after_fixed_number_of_answers(self) -> None:
        self.fx.setup_admin()
        for name in ["Ada", "Bob", "Cy"]:
            self.fx.add_user(name)
        alarm = self.fx.create_alarm(
            mode="challenge",
            participants=[1, 2, 3],
            completion_mode="count",
            target_count=2,
        )
        event = self.fx.ring(alarm["id"])
        state = self.fx.state()
        tokens = [c["token"] for c in state["active_events"][0]["challenges"]]
        first = self.fx.solve(tokens[0])
        self.assertFalse(first["all_done"])
        second = self.fx.solve(tokens[1])
        self.assertTrue(second["all_done"])
        self.assertEqual(second["answer"]["state"], "completed")
        self.assertEqual(second["answer"]["stop_reason"], "answered by 2 of 3 users")
        # The third link is closed because the target was reached.
        status, data, _ = self.fx.client.request(
            "POST", f"/api/s/{tokens[2]}/answer", {"answer": "1"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "closed")
        state = self.fx.state()
        self.assertEqual(state["active_events"], [])
        self.assertEqual(state["history"][0]["completion_mode"], "count")
        self.assertEqual(state["history"][0]["target_count"], 2)
        self.assertEqual(state["history"][0]["stop_reason"], "answered by 2 of 3 users")


class SingleSnoozeTests(ApiBase):
    def test_single_user_challenge_can_snooze(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(mode="challenge", participants=[1])
        event = self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/snooze", {}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["event"]["state"], "snoozed")
        self.assertTrue(data["event"]["snooze_allowed"])
        self.fx.client.request("POST", f"/api/events/{event['id']}/stop", {"force": False})

    def test_multi_user_challenge_cannot_snooze(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_user("Bob")
        alarm = self.fx.create_alarm(mode="challenge", participants=[1, 2])
        event = self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "POST", f"/api/events/{event['id']}/snooze", {}
        )
        self.assertEqual(status, 409)
        self.assertIn("more than one", data["error"])
        self.fx.client.request("POST", f"/api/events/{event['id']}/stop", {"force": True})


class CustomQuestionTests(ApiBase):
    def test_custom_text_question_flow(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_user("Bob")
        self.fx.add_question("What is 猫 in English?", "Cat")
        alarm = self.fx.create_alarm(
            mode="challenge",
            participants=[1, 2],
            question_source="custom",
        )
        event = self.fx.ring(alarm["id"])
        state = self.fx.state()
        ch = state["active_events"][0]["challenges"][0]
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(data["challenge"]["answer_type"], "text")
        self.assertEqual(data["challenge"]["question"], "What is 猫 in English?")
        wrong = self.fx.answer(ch["token"], "Dog")
        self.assertEqual(wrong["status"], "wrong")
        correct = self.fx.answer(ch["token"], "  CAT ")
        self.assertEqual(correct["status"], "correct")

    def test_question_crud(self) -> None:
        self.fx.setup_admin()
        q = self.fx.add_question("Q1", "A1")
        status, data, _ = self.fx.client.request(
            "PUT", f"/api/questions/{q['id']}", {"question": "Q2", "answer": "A2"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["question"]["question"], "Q2")
        status, data, _ = self.fx.client.request("GET", "/api/questions")
        self.assertEqual(len(data["questions"]), 1)
        status, _data, _ = self.fx.client.request("DELETE", f"/api/questions/{q['id']}")
        self.assertEqual(status, 200)
        status, _data, _ = self.fx.client.request("DELETE", f"/api/questions/{q['id']}")
        self.assertEqual(status, 404)


class MusicTests(ApiBase):
    def test_upload_stream_and_use_music(self) -> None:
        self.fx.setup_admin()
        wav = self.fx.tmp / "test.wav"
        build_beep(wav)
        raw = wav.read_bytes()
        status, body, headers = self.fx.client.request_bytes(
            "POST", "/api/music?name=sunrise.wav&display=Sunrise", raw, "audio/wav"
        )
        self.assertEqual(status, 201, body)
        music = json.loads(body)["music"]
        self.assertEqual(music["name"], "Sunrise")
        music_id = music["id"]

        status, part, headers = self.fx.client.request_bytes(
            "GET", f"/api/music/{music_id}/file", headers={"Range": "bytes=0-99"}
        )
        self.assertEqual(status, 206)
        self.assertEqual(len(part), 100)
        self.assertIn("bytes 0-99/", headers.get("Content-Range", ""))

        alarm = self.fx.create_alarm(music_id=music_id)
        event = self.fx.ring(alarm["id"])
        state = self.fx.state()
        self.assertEqual(state["active_events"][0]["music_name"], "Sunrise")
        status, data, _ = self.fx.client.request(
            "DELETE", f"/api/music/{music_id}"
        )
        self.assertEqual(status, 409)
        self.assertIn("still used", data["error"])
        self.fx.client.request("POST", f"/api/events/{event['id']}/stop", {"force": False})
        self.fx.client.request("DELETE", f"/api/alarms/{alarm['id']}")
        status, _data, _ = self.fx.client.request("DELETE", f"/api/music/{music_id}")
        self.assertEqual(status, 200)
        self.assertEqual(self.fx.state()["music"], [])

    def test_rejects_unsupported_upload(self) -> None:
        self.fx.setup_admin()
        status, body, _ = self.fx.client.request_bytes(
            "POST", "/api/music?name=evil.exe", b"MZ", "application/octet-stream"
        )
        self.assertEqual(status, 400)
        self.assertIn("Unsupported", json.loads(body)["error"])


class ShortlinkTests(ApiBase):
    def test_public_link_claim_and_qr(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_user("Bob")
        alarm = self.fx.create_alarm(
            mode="challenge",
            participants=[1, 2],
            slug="alarmmorning",
        )
        self.assertEqual(alarm["link"], f"http://127.0.0.1:{self.fx.port}/alarmmorning")

        status, body, headers = self.fx.client.request_bytes("GET", "/alarmmorning")
        self.assertEqual(status, 200)
        self.assertIn("alarm.js", body.decode())

        status, body, headers = self.fx.client.request_bytes("GET", "/qr/alarmmorning.svg")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Content-Type"), "image/svg+xml")
        self.assertIn(b"<svg", body)

        status, data, _ = self.fx.client.request("GET", "/api/alarm/alarmmorning")
        self.assertEqual(status, 200)
        self.assertEqual(data["state"], "idle")
        self.assertEqual(len(data["participants"]), 2)

        status, data, _ = self.fx.client.request(
            "POST",
            "/api/alarms",
            {
                "label": "Duplicate",
                "time": "08:00",
                "days": [1, 2, 3, 4, 5],
                "mode": "challenge",
                "participants": [1],
                "slug": "alarmmorning",
                "enabled": True,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("already in use", data["error"])

        status, data, _ = self.fx.client.request(
            "POST",
            "/api/alarms",
            {
                "label": "Reserved",
                "time": "08:01",
                "days": [1, 2, 3, 4, 5],
                "mode": "challenge",
                "participants": [1],
                "slug": "api",
                "enabled": True,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("reserved", data["error"])

        event = self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request("GET", "/api/alarm/alarmmorning")
        self.assertEqual(status, 200)
        self.assertEqual(data["state"], "ringing")
        self.assertNotIn("token", data["event"]["challenges"][0])

        status, data, _ = self.fx.client.request(
            "POST", "/api/alarm/alarmmorning/claim", {"user_id": 1}
        )
        self.assertEqual(status, 200)
        token1 = data["url"].rsplit("/", 1)[1]
        self.assertTrue(self.fx.answer(token1, self._answer_for(token1))["status"] == "correct")

        status, data, _ = self.fx.client.request(
            "POST", "/api/alarm/alarmmorning/claim", {"user_id": 2}
        )
        self.assertEqual(status, 200)
        token2 = data["url"].rsplit("/", 1)[1]
        result = self.fx.answer(token2, self._answer_for(token2))
        self.assertTrue(result["all_done"])

        status, data, _ = self.fx.client.request("GET", "/api/alarm/alarmmorning")
        self.assertEqual(data["state"], "idle")
        self.assertEqual(data["last_event"]["state"], "completed")
        status, data, _ = self.fx.client.request(
            "POST", "/api/alarm/alarmmorning/claim", {"user_id": 2}
        )
        self.assertEqual(status, 409)

    def _answer_for(self, token: str) -> str:
        status, data, _ = self.fx.client.request("GET", f"/api/s/{token}")
        assert status == 200
        question = data["challenge"]["question"]
        return str(int(eval(question.replace("×", "*").replace("−", "-"), {"__builtins__": {}}, {})))

    def test_unknown_public_link(self) -> None:
        self.fx.setup_admin()
        status, _data, _ = self.fx.client.request("GET", "/api/alarm/nope")
        self.assertEqual(status, 404)
        status, _body, _ = self.fx.client.request_bytes("GET", "/qr/nope.svg")
        self.assertEqual(status, 404)


class CalendarTests(ApiBase):
    def test_import_use_and_delete_calendar(self) -> None:
        self.fx.setup_admin()
        cal = self.fx.add_calendar(
            "China test",
            "日期,类型,备注\n2026-10-26,holiday,调休休息\n2026-11-01,working,调休上班\n",
        )
        self.assertEqual(cal["day_count"], 2)
        self.assertEqual(cal["working_days"], 1)
        self.assertEqual(cal["holiday_days"], 1)
        alarm = self.fx.create_alarm(calendar_id=cal["id"])
        state = self.fx.state()
        stored = next(a for a in state["alarms"] if a["id"] == alarm["id"])
        self.assertEqual(stored["calendar_id"], cal["id"])
        self.assertEqual(stored["calendar_name"], "China test")
        self.assertEqual(state["calendars"][0]["alarms_using"], 1)

        status, data, _ = self.fx.client.request("DELETE", f"/api/calendars/{cal['id']}")
        self.assertEqual(status, 200)
        state = self.fx.state()
        stored = next(a for a in state["alarms"] if a["id"] == alarm["id"])
        self.assertIsNone(stored["calendar_id"])
        self.assertEqual(state["calendars"], [])

    def test_invalid_calendar_csv(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request(
            "POST", "/api/calendars", {"name": "Bad", "csv": "date,type\n2026-99-99,holiday\n"}
        )
        self.assertEqual(status, 400)
        self.assertIn("invalid date", data["error"])


class DeviceSettingsTests(ApiBase):
    def test_audio_device_setting_and_detection(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request("GET", "/api/audio/devices")
        self.assertEqual(status, 200)
        self.assertEqual(data["devices"][0]["value"], "")
        status, data, _ = self.fx.client.request(
            "POST",
            "/api/settings",
            {"timezone": "UTC", "base_url": "", "audio_device": "speaker"},
        )
        self.assertEqual(status, 400)
        status, data, _ = self.fx.client.request(
            "POST",
            "/api/settings",
            {"timezone": "UTC", "base_url": "", "audio_device": "alsa:default"},
        )
        self.assertEqual(status, 200)
        state = self.fx.state()
        self.assertEqual(state["settings"]["audio_device"], "alsa:default")
        self.assertEqual(state["audio"]["device"], "alsa:default")


class TypedChallengeTests(ApiBase):
    def test_choice_challenge(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_question(
            "Which colour is the sky?", "Blue", "choice",
            ["Red", "Blue", "Green", "Yellow"],
        )
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1], challenge_type="choice"
        )
        event = self.fx.ring(alarm["id"])
        self.assertEqual(event["challenge_type"], "choice")
        state = self.fx.state()
        ch = state["active_events"][0]["challenges"][0]
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(data["challenge"]["challenge_type"], "choice")
        self.assertEqual(
            data["challenge"]["payload"]["options"],
            ["Red", "Blue", "Green", "Yellow"],
        )
        wrong = self.fx.answer(ch["token"], "Green")
        self.assertEqual(wrong["status"], "wrong")
        correct = self.fx.answer(ch["token"], "Blue")
        self.assertEqual(correct["status"], "correct")
        self.assertTrue(correct["all_done"])

    def test_color_challenge(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1], challenge_type="color"
        )
        self.fx.ring(alarm["id"])
        ch = self.fx.state()["active_events"][0]["challenges"][0]
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        payload = data["challenge"]["payload"]
        self.assertEqual(len(payload["options"]), 4)
        wrong = next(c["key"] for c in payload["options"] if c["key"] != payload["target"]["key"])
        self.assertEqual(self.fx.answer(ch["token"], wrong)["status"], "wrong")
        # A fresh colour question was issued; fetch its target.
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        target = data["challenge"]["payload"]["target"]["key"]
        result = self.fx.answer(ch["token"], target)
        self.assertEqual(result["status"], "correct")
        self.assertTrue(result["all_done"])

    def test_pattern_challenge(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1], challenge_type="pattern"
        )
        self.fx.ring(alarm["id"])
        ch = self.fx.state()["active_events"][0]["challenges"][0]
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        payload = data["challenge"]["payload"]
        self.assertEqual(payload["size"], 3)
        self.assertFalse(self.fx.answer(ch["token"], payload["target"][:-1])["status"] == "correct")
        # Wrong answers rotate the pattern; read the new one and paint it.
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        target = data["challenge"]["payload"]["target"]
        result = self.fx.answer(ch["token"], target)
        self.assertEqual(result["status"], "correct")
        self.assertTrue(result["all_done"])

    def test_choice_question_validation(self) -> None:
        self.fx.setup_admin()
        for payload in [
            {"question": "Q", "answer": "A", "kind": "choice", "options": ["A"]},
            {"question": "Q", "answer": "A", "kind": "choice", "options": ["B", "C"]},
            {"question": "Q", "answer": "A", "kind": "choice", "options": ["A", "A"]},
            {"question": "Q", "answer": "A", "kind": "nope", "options": ["A", "B"]},
        ]:
            status, _data, _ = self.fx.client.request("POST", "/api/questions", payload)
            self.assertEqual(status, 400, payload)


class SkipNextTests(ApiBase):
    def test_skip_next_api_flag(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm()
        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarms/{alarm['id']}/skip", {"skip": True}
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["alarm"]["skip_next"])
        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarms/{alarm['id']}/skip", {"skip": False}
        )
        self.assertEqual(status, 200)
        self.assertFalse(data["alarm"]["skip_next"])


class StaticAssetTests(ApiBase):
    def test_i18n_asset_is_served(self) -> None:
        status, body, headers = self.fx.client.request("GET", "/i18n.js")
        self.assertEqual(status, 200)
        self.assertIn("unzzz.lang", body)
        self.assertIn("data-lang-select", body)
        self.assertIn("javascript", headers.get("Content-Type", "").lower())


class LinkRetentionTests(ApiBase):
    def test_links_retire_after_configured_minutes(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1], challenge_type="math",
            slug="retention-test",
        )
        event = self.fx.ring(alarm["id"])
        ch = event["challenges"][0]
        self.assertEqual(self.fx.answer(ch["token"], "999999999")["status"], "wrong")
        # Get a fresh, solvable question and complete it.
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(status, 200)
        # Use a one-answer event; solve by reading the generated arithmetic.
        question = data["challenge"]["question"]
        answer = str(eval(question.replace("×", "*").replace("−", "-")))
        result = self.fx.answer(ch["token"], answer)
        self.assertEqual(result["status"], "correct")
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(status, 200)
        self.assertEqual(data["challenge"]["state"], "completed")

        state = self.fx.state()
        self.assertEqual(state["settings"]["link_retention_minutes"], 30)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/settings",
            {"timezone": state["timezone"], "base_url": "",
             "audio_device": "", "link_retention_minutes": 0},
        )
        self.assertEqual(status, 200)
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(status, 410)
        self.assertIn("expired", data["error"].lower())
        status, data, _ = self.fx.client.request("GET", "/api/alarm/retention-test")
        self.assertEqual(status, 200)
        self.assertIsNone(data["last_event"])

    def test_retention_validation(self) -> None:
        self.fx.setup_admin()
        state = self.fx.state()
        status, _data, _ = self.fx.client.request(
            "POST", "/api/settings",
            {"timezone": state["timezone"], "base_url": "",
             "audio_device": "", "link_retention_minutes": 99999},
        )
        self.assertEqual(status, 400)


class MusicPreviewTests(ApiBase):
    def test_server_preview_start_stop(self) -> None:
        self.fx.setup_admin()
        music = self.fx.store.add_music("Preview", "preview.wav", "audio/wav", 1)
        path = self.fx.tmp / "music" / "preview.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"RIFF")
        audio = self.fx.engine.audio
        preview_player = self.fx.tmp / "preview-player.sh"
        preview_player.write_text("#!/bin/sh\nsleep 10\n")
        preview_player.chmod(0o755)
        audio.mode = "custom"
        audio.custom_argv = [str(preview_player)]
        status, data, _ = self.fx.client.request(
            "POST", f"/api/music/{music['id']}/test", {}
        )
        self.assertEqual(status, 200, data)
        self.assertTrue(data["music_preview"]["playing"])
        self.assertEqual(
            self.fx.state()["music_preview"]["music_id"], music["id"]
        )
        status, data, _ = self.fx.client.request(
            "POST", f"/api/music/{music['id']}/stop", {}
        )
        self.assertEqual(status, 200, data)
        self.assertFalse(data["music_preview"]["playing"])


class VolumeSettingsTests(ApiBase):
    def test_target_volume_validation_and_state(self) -> None:
        self.fx.setup_admin()
        state = self.fx.state()
        self.assertEqual(state["volume"]["target"], 80)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/settings",
            {"timezone": state["timezone"], "base_url": "",
             "audio_device": "", "target_volume": 55},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.fx.state()["volume"]["target"], 55)
        status, _data, _ = self.fx.client.request(
            "POST", "/api/settings",
            {"timezone": state["timezone"], "base_url": "",
             "audio_device": "", "target_volume": 101},
        )
        self.assertEqual(status, 400)


class QuestionImportTests(ApiBase):
    def test_import_multiple_choice_csv(self) -> None:
        self.fx.setup_admin()
        csv = (
            "question,option a,option b,option c,option d,correct answer\n"
            "Which one is a colour?,Red,Green,Blue,Yellow,b\n"
            "2+2?,3,4,5,6,b\n"
        )
        status, data, _ = self.fx.client.request(
            "POST", "/api/questions/import", {"csv": csv}
        )
        self.assertEqual(status, 201, data)
        self.assertEqual(data["imported"], 2)
        state = self.fx.state()
        self.assertEqual(len(state["questions"]), 2)
        imported = next(q for q in state["questions"] if q["question"].startswith("Which"))
        self.assertEqual(imported["kind"], "choice")
        self.assertEqual(imported["options"], ["Red", "Green", "Blue", "Yellow"])
        self.assertEqual(imported["answer"], "Green")

    def test_import_rejects_bad_answer(self) -> None:
        self.fx.setup_admin()
        status, data, _ = self.fx.client.request(
            "POST", "/api/questions/import",
            {"csv": "Q,a,b,c,d,z\n"},
        )
        self.assertEqual(status, 400)
        self.assertIn("correct answer", data["error"])


class ChallengeCountTests(ApiBase):
    def test_participant_must_pass_multiple_challenges(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1], challenge_type="math",
            challenge_count=2, slug="two-challenges",
        )
        event = self.fx.ring(alarm["id"])
        ch = event["challenges"][0]
        for expected_solved, final in ((1, False), (2, True)):
            status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
            self.assertEqual(data["challenge"]["required"], 2)
            question = data["challenge"]["question"]
            answer = str(eval(question.replace("×", "*").replace("−", "-")))
            result = self.fx.answer(ch["token"], answer)
            self.assertEqual(result["status"], "correct")
            self.assertEqual(result["answer"]["solved"], expected_solved)
            self.assertEqual(result["all_done"], final)
        status, data, _ = self.fx.client.request("GET", f"/api/s/{ch['token']}")
        self.assertEqual(data["challenge"]["state"], "completed")

    def test_challenge_count_validation(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        status, _data, _ = self.fx.client.request(
            "POST", "/api/alarms",
            {"label": "Bad count", "time": "07:30", "days": [1],
             "mode": "challenge", "participants": [1],
             "challenge_type": "math", "challenge_count": 11, "slug": "badcount"},
        )
        self.assertEqual(status, 400)


class RandomChoiceTests(ApiBase):
    def test_random_choice_uses_shared_first_question(self) -> None:
        self.fx.setup_admin()
        self.fx.add_user("Ada")
        self.fx.add_user("Bob")
        self.fx.add_question("Q1", "A", "choice", ["A", "B", "C", "D"])
        self.fx.add_question("Q2", "B", "choice", ["A", "B", "C", "D"])
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[1, 2],
            challenge_type="random_choice", challenge_count=2,
            slug="random-choice",
        )
        event = self.fx.ring(alarm["id"])
        self.assertEqual(event["challenge_type"], "random_choice")
        state = self.fx.state()["active_events"][0]
        tokens = [c["token"] for c in state["challenges"]]
        states = []
        for token in tokens:
            _status, data, _ = self.fx.client.request("GET", f"/api/s/{token}")
            states.append(data["challenge"])
        self.assertEqual(states[0]["question"], states[1]["question"])
        self.assertEqual(states[0]["payload"], states[1]["payload"])
        self.assertEqual(states[0]["required"], 2)
        stored = self.fx.store.get_event(event["id"])
        shared = json.loads(stored["shared_questions"])
        self.assertEqual(len(shared), 2)
        challenge = self.fx.store.get_challenge_by_token(tokens[0])
        result = self.fx.answer(tokens[0], challenge["answer"])
        self.assertEqual(result["status"], "correct")
        self.assertFalse(result["all_done"])
        self.assertEqual(result["answer"]["solved"], 1)
        _status, next_question, _ = self.fx.client.request("GET", f"/api/s/{tokens[0]}")
        self.assertEqual(next_question["challenge"]["question"], shared[1]["question"])
        _status, other_question, _ = self.fx.client.request("GET", f"/api/s/{tokens[1]}")
        self.assertEqual(other_question["challenge"]["question"], shared[0]["question"])


class PublicStandardLinkTests(ApiBase):
    def test_standard_alarm_link_can_stop(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm()
        self.assertTrue(alarm["slug"])
        event = self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "GET", f"/api/alarm/{alarm['slug']}"
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(data["event"]["mode"], "standard")
        before = time.time()
        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarm/{alarm['slug']}/stop", {}
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(data["event"]["state"], "stopped")
        alarm = self.fx.store.get_alarm(alarm["id"])
        self.assertIsNone(alarm["link_expires_at"])

        status, _data, _ = self.fx.client.request(
            "POST", f"/api/alarms/{alarm['id']}/toggle", {"enabled": False}
        )
        self.assertEqual(status, 200)
        alarm = self.fx.store.get_alarm(alarm["id"])
        self.assertGreaterEqual(alarm["link_expires_at"], before + 6 * 3600 - 2)

        self.fx.store.set_alarm_link_expiry(alarm["id"], time.time() - 1)
        status, data, _ = self.fx.client.request(
            "GET", f"/api/alarm/{alarm['slug']}"
        )
        self.assertEqual(status, 410)

    def test_standard_alarm_link_can_snooze(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm(max_snoozes=1, snooze_minutes=1)
        self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "POST", f"/api/alarm/{alarm['slug']}/snooze", {}
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(data["event"]["state"], "snoozed")

    def test_link_can_be_modified_and_listed(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm()
        state = self.fx.state()
        item = next(x for x in state["links"] if x["kind"] == "alarm")
        self.assertEqual(item["slug"], alarm["slug"])
        new_slug = "my-new-link"
        expiry = time.time() + 7200
        status, data, _ = self.fx.client.request(
            "PUT", f"/api/links/alarm/{alarm['id']}",
            {"slug": new_slug, "expires_at": expiry},
        )
        self.assertEqual(status, 200, data)
        state = self.fx.state()
        item = next(x for x in state["links"] if x["kind"] == "alarm")
        self.assertEqual(item["slug"], new_slug)
        self.assertAlmostEqual(item["expires_at"], expiry, delta=2)
        status, _data, _ = self.fx.client.request("GET", f"/api/alarm/{alarm['slug']}")
        self.assertEqual(status, 404)
        status, _data, _ = self.fx.client.request("GET", f"/{new_slug}")
        self.assertEqual(status, 200)

    def test_deleted_alarm_link_remains_for_six_hours(self) -> None:
        self.fx.setup_admin()
        alarm = self.fx.create_alarm()
        slug = alarm["slug"]
        status, _data, _ = self.fx.client.request("DELETE", f"/api/alarms/{alarm['id']}")
        self.assertEqual(status, 200)
        status, body, _ = self.fx.client.request("GET", f"/{slug}")
        self.assertEqual(status, 200)
        self.assertIn("was removed", str(body))
        retired = self.fx.store.get_retired_link(slug)
        self.assertIsNotNone(retired)
        self.assertGreater(retired["expires_at"], time.time() + 6 * 3600 - 5)
        with self.fx.store.tx() as c:
            c.execute(
                "UPDATE retired_links SET expires_at=? WHERE slug=?",
                (time.time() - 1, slug),
            )
        status, _body, _ = self.fx.client.request("GET", f"/{slug}")
        self.assertEqual(status, 410)


class AllInOneLinkTests(ApiBase):
    def test_all_link_redirects_to_recent_challenge(self) -> None:
        self.fx.setup_admin()
        user = self.fx.add_user("Ada")
        alarm = self.fx.create_alarm(
            mode="challenge", participants=[user["id"]],
            challenge_type="math", slug="challenge-link",
        )
        self.fx.ring(alarm["id"])
        status, data, _ = self.fx.client.request(
            "POST", "/api/links/all", {"slug": "all"}
        )
        self.assertEqual(status, 201, data)
        self.assertEqual(data["link"]["kind"], "all")
        self.assertEqual(data["link"]["slug"], "all")

        status, body, headers = self.fx.client.request("GET", "/qr/all.svg")
        self.assertEqual(status, 200)
        self.assertIn("<svg", body)

        import urllib.error
        import urllib.request
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        try:
            opener.open(self.fx.client.base + "/all", timeout=5)
            self.fail("expected a redirect")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 302)
            self.assertEqual(exc.headers.get("Location"), "/challenge-link")
            exc.close()

    def test_all_link_expiry(self) -> None:
        self.fx.setup_admin()
        self.fx.client.request("POST", "/api/links/all", {"slug": "all"})
        self.fx.client.request(
            "PUT", "/api/links/all", {"slug": "all", "expires_at": time.time() - 1}
        )
        status, _data, _ = self.fx.client.request("GET", "/all")
        self.assertEqual(status, 410)
