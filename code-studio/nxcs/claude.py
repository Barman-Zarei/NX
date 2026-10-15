"""Claude API client (Messages API) using urllib. No key is ever logged or stored in project files.

Key sources, in order: explicit argument, env ANTHROPIC_API_KEY, key file (mode 0600) under the
user's config dir. `transport` can be injected for tests; responses from an injected transport are
flagged source="mock" so a mock can never be mistaken for a real Claude reply.
"""
import json, os, stat, threading, urllib.error, urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
KEY_FILE = os.path.join(os.path.expanduser("~"), ".config", "nx-code-studio", "anthropic.key")


class ClaudeError(Exception):
    def __init__(self, kind, message, status=None):
        super().__init__(message)
        self.kind, self.status = kind, status


def save_key(key, path=KEY_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(key.strip())
    os.chmod(path, 0o600)


def load_key(path=KEY_FILE):
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k.strip()
    try:
        if os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ClaudeError("insecure_key_file", "key file must be mode 0600")
        with open(path) as f:
            return f.read().strip() or None
    except OSError:
        return None


def redact(text, key):
    return text.replace(key, "***") if key and text else text


class Client:
    def __init__(self, model="claude-sonnet-4-6", api_key=None, enabled=True, transport=None,
                 timeout=60, max_tokens=1024):
        self.model, self.enabled, self.timeout, self.max_tokens = model, enabled, timeout, max_tokens
        self._key, self._transport = api_key, transport
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def ask(self, prompt, system=None, context_files=None):
        if not self.enabled:
            raise ClaudeError("disabled", "AI features are disabled")
        self._cancel.clear()
        content = prompt
        for name, text in (context_files or {}).items():
            content += "\n\n--- file: %s ---\n%s" % (name, text)
        body = {"model": self.model, "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": content}]}
        if system:
            body["system"] = system
        if self._transport:
            data = self._transport(body)
            source = "mock"
        else:
            key = self._key or load_key()
            if not key:
                raise ClaudeError("no_key", "no API key configured")
            data, source = self._http(body, key), "claude-api"
        if self._cancel.is_set():
            raise ClaudeError("cancelled", "request cancelled")
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return {"text": text, "source": source, "usage": data.get("usage", {}), "model": data.get("model")}

    def _http(self, body, key):
        req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
            "content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            msg = redact(e.read().decode("utf-8", "replace")[:300], key)
            kind = {401: "auth", 403: "auth", 429: "rate_limit"}.get(e.code, "server" if e.code >= 500 else "request")
            raise ClaudeError(kind, msg, e.code)
        except (urllib.error.URLError, OSError) as e:
            raise ClaudeError("network", redact(str(e), key))
