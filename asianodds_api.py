#!/usr/bin/env python3
import time
import json
import requests
from datetime import datetime

DEFAULT_TIMEOUT = (5, 10) # (connect, read)

class AOAuthError(Exception): ...
class AORequestError(Exception): ...

class AsianOddsSession:
    def __init__(self, base_url: str, username: str, password: str, is_md5: bool = True, log_path: str = None):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.is_md5 = is_md5
        self.key = None # AOKey
        self.token = None # AOToken
        self.url = None # session-scoped url
        self.last_login_ts = None
        self.log_path = log_path

    def _log(self, msg: str):
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")
        except Exception:
            pass

    def login(self, retries: int = 3, backoff: float = 1.0):
        params = {"username": self.username, "password": self.password}
        url = f"{self.base_url}/Login"
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, params=params, headers={"accept": "application/json"}, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                code = data.get("Code")
                if code == 0:
                    result = data.get("Result", {})
                    self.key = result.get("Key")
                    self.token = result.get("Token")
                    self.url = result.get("Url") or self.base_url
                    self.last_login_ts = time.time()
                    self._log(f"LOGIN OK | latency_ms={int(resp.elapsed.total_seconds()*1000)}")
                    return True
                else:
                    txt = (data.get("Result") or {}).get("TextMessage", "Unknown error")
                    last_err = f"LOGIN FAIL code={code} msg={txt}"
                    self._log(last_err)
            except requests.RequestException as e:
                last_err = f"LOGIN REQ ERROR: {e}"
                self._log(last_err)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30.0)
        raise AOAuthError(last_err or "LOGIN FAILED")

    def is_authenticated(self) -> bool:
        return bool(self.key and self.token)

    def health_probe(self) -> dict:
        """Return a small dict summarizing API health."""
        age = None
        if self.last_login_ts:
            age = int(time.time() - self.last_login_ts)
        return {
            "authenticated": self.is_authenticated(),
            "token_age_s": age,
            "session_url": self.url,
            "username": self.username,
        }

    # Example protected call (extend later for odds, place bet, etc.)
    def _auth_params(self) -> dict:
        if not self.is_authenticated():
            raise AOAuthError("Not authenticated")
        return {"key": self.key, "token": self.token}

    def get_time(self) -> dict:
        # A lightweight endpoint to test auth could be added here if available.
        # Placeholder returns health info only.
        return self.health_probe()
