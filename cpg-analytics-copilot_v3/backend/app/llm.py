"""Groq LLM wrapper with telemetry (OBS-004) and graceful fallback."""
import json
import logging
import time

from .config import settings
from .logging_setup import log, request_id_var
from .telemetry import record_llm

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None


class LLMUnavailable(Exception):
    pass


class LLM:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key) if (Groq and settings.groq_api_key) else None

    @property
    def available(self):
        return self.client is not None

    def _call(self, model, messages, tools, purpose, temperature, json_mode, max_tokens):
        t0 = time.time(); kw = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if tools:
            kw.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        try:
            r = self.client.chat.completions.create(**kw)
            u = getattr(r, "usage", None)
            record_llm(request_id_var.get(), model, purpose, (time.time() - t0) * 1000, "ok", getattr(u, "prompt_tokens", 0), getattr(u, "completion_tokens", 0))
            return r.choices[0].message
        except Exception as e:
            record_llm(request_id_var.get(), model, purpose, (time.time() - t0) * 1000, "error", error=str(e))
            log("llm", logging.WARNING, "llm call failed", model=model, purpose=purpose, error=str(e)[:200])
            raise

    def chat(self, messages, tools=None, purpose="chat", temperature=0.1, json_mode=False, max_tokens=1400):
        if not self.available:
            raise LLMUnavailable()
        try:
            return self._call(settings.groq_model, messages, tools, purpose, temperature, json_mode, max_tokens)
        except Exception:
            try:  # one retry on the fast model (rate limit / tool_use_failed)
                return self._call(settings.groq_fast_model, messages, tools, purpose + ":fallback", 0.0, json_mode, max_tokens)
            except Exception as e:
                raise LLMUnavailable(str(e))

    def json(self, system, user, purpose="json", max_tokens=900):
        m = self.chat([{"role": "system", "content": system + " Respond with a single JSON object only."}, {"role": "user", "content": user}], purpose=purpose, json_mode=True, max_tokens=max_tokens)
        return json.loads(m.content)


llm = LLM()
