#!/usr/bin/env python3
import time, requests
from datetime import datetime

DEFAULT_TIMEOUT = (5, 10) # connect, read

class AOAuthError(Exception): ...
class AORequestError(Exception): ...

class AsianOddsSession:
    def __init__(self, base_url, username, password, is_md5=True, log_path=None):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.is_md5 = is_md5
        self.key = None
        self.token = None
        self.url = None
        self.last_login_ts = None
        self.log_path = log_path

    def _log(self, msg):
        if not self.log_path: return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {msg}\n")
        except Exception:
            pass

    def login(self, retries=3, backoff=1.0):
        last_err = None
        for _ in range(retries):
            try:
                r = requests.get(
                    f"{self.base_url}/Login",
                    params={"username": self.username, "password": self.password},
                    headers={"accept": "application/json"},
                    timeout=DEFAULT_TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
                if data.get("Code") == 0:
                    res = data.get("Result") or {}
                    self.key = res.get("Key")
                    self.token = res.get("Token")
                    self.url = res.get("Url") or self.base_url
                    self.last_login_ts = time.time()
                    self._log(f"LOGIN OK | latency_ms={int(r.elapsed.total_seconds()*1000)}")
                    return True
                last_err = (data.get("Result") or {}).get("TextMessage", "Unknown error")
                self._log(f"LOGIN FAIL | {last_err}")
            except requests.RequestException as e:
                last_err = str(e)
                self._log(f"LOGIN REQ ERROR | {last_err}")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
        raise AOAuthError(last_err or "Login failed")

    def is_authenticated(self):
        return bool(self.key and self.token)

    def health_probe(self):
        age = int(time.time() - self.last_login_ts) if self.last_login_ts else None
        return {"authenticated": self.is_authenticated(), "token_age_s": age, "session_url": self.url, "username": self.username}

    def ensure_alive(self, max_age_s=3600):
        """Re-login if token age exceeds threshold or if not authenticated."""
        if not self.is_authenticated():
            self.login()
            return
        age = int(time.time() - self.last_login_ts)
        if max_age_s and age >= max_age_s:
            self._log("TOKEN REFRESH")
            self.login()
