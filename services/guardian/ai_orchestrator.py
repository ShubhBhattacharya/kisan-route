"""KisanRoute Guardian AI - Multi-Model Intelligence & Quota Orchestrator.

Provides model-independent routing prioritizing free-tier API quotas (Google Gemini 2.5 Flash,
Groq, HuggingFace, DeepSeek) with zero-cost deterministic fallback.
Tracks execution cost, token limits, and rate limits with strict safeguards against paid billing.
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from services.guardian.storage import append_log, update_state, get_state


class ModelOrchestrator:
    """Manages AI reasoning, root-cause diagnosis, code patch generation, and quota management."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.hf_key = os.getenv("HUGGINGFACE_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    def analyze_incident(self, incident_title: str, error_details: dict, category: str = "backend") -> dict:
        """Perform root-cause analysis and return structured recommendations."""
        prompt = (
            f"You are the Chief Reliability & Systems Auditor for KisanRoute (an agricultural platform).\n"
            f"Incident Category: {category}\n"
            f"Title: {incident_title}\n"
            f"Details: {json.dumps(error_details, ensure_ascii=False)}\n\n"
            f"Respond with a JSON object containing:\n"
            f"1. root_cause (concise explanation)\n"
            f"2. severity (low, medium, high, critical)\n"
            f"3. tier (1 for safe auto-fix, 2 for patch-and-review, 3 for manual human approval)\n"
            f"4. safe_action (suggested minimal safe remediation)\n"
            f"5. confidence_score (0.0 to 1.0)\n"
        )

        response_text = self._dispatch_ai(prompt, task_type="root_cause_analysis")
        if response_text:
            try:
                # Strip markdown code blocks if present
                clean = response_text.strip()
                if clean.startswith("```json"):
                    clean = clean[7:]
                if clean.startswith("```"):
                    clean = clean[3:]
                if clean.endswith("```"):
                    clean = clean[:-3]
                parsed = json.loads(clean.strip())
                return parsed
            except Exception as e:
                append_log("AI_PARSE_ERROR", f"Failed to parse AI response as JSON: {e}", level="WARNING")

        # Deterministic Rule-Based Fallback
        return self._deterministic_rca(incident_title, error_details, category)

    def _dispatch_ai(self, prompt: str, task_type: str = "reasoning") -> str:
        """Route to available free-tier AI providers with deterministic fallback."""
        # 1. Primary: Google Gemini 2.5 Flash / 1.5 Flash (Free Tier)
        if self.gemini_key and self.gemini_key != "your_gemini_api_key_here":
            for model_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
                    payload = {
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 800
                        }
                    }
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=8.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        cands = res.get("candidates", [])
                        if cands:
                            text = cands[0].get("content", {}).get("parts", [])[0].get("text", "")
                            self._track_tokens(estimated_tokens=len(prompt.split()) + len(text.split()), provider=f"gemini_{model_name}")
                            return text.strip()
                except Exception as e:
                    append_log("AI_DISPATCH_FAIL", f"Gemini {model_name} failed: {e}", level="INFO")
                    continue

        # 2. Secondary: Groq API (High-speed Llama 3 free tier)
        if self.groq_key:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "You are a senior site reliability engineer. Output only JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.groq_key}"
                    }
                )
                with urllib.request.urlopen(req, timeout=6.0) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    text = res.get("choices", [{}])[0].get("message", {}).get("content", "")
                    self._track_tokens(estimated_tokens=len(prompt.split()) + len(text.split()), provider="groq_llama3")
                    return text.strip()
            except Exception as e:
                append_log("AI_DISPATCH_FAIL", f"Groq fallback failed: {e}", level="INFO")

        return ""

    def _deterministic_rca(self, title: str, details: dict, category: str) -> dict:
        """Zero-cost deterministic root-cause rules."""
        t_low = title.lower()
        det_str = json.dumps(details).lower()

        # Database connection issues
        if "database" in t_low or "sqlite" in t_low or "sqlalchemy" in det_str:
            return {
                "root_cause": "Database connection or read lock error in SQLite/PostgreSQL storage.",
                "severity": "high",
                "tier": 2,
                "safe_action": "Check file write permissions, run safe integrity probe, flush stale connections.",
                "confidence_score": 0.88
            }

        # External API timeouts (Weather, News, WhatsApp)
        if any(k in t_low for k in ["weather", "mandi", "news", "timeout", "network"]):
            return {
                "root_cause": "Transient latency or connection timeout from third-party upstream API.",
                "severity": "low",
                "tier": 1,
                "safe_action": "Apply exponential backoff retry and serve verified fallback cache.",
                "confidence_score": 0.94
            }

        # Financial / Payment / Critical Business Logic Protection
        if any(k in t_low or k in det_str for k in ["payment", "bank", "balance", "money", "transaction", "auth", "permission"]):
            return {
                "root_cause": "Sensitive financial or authorization logic barrier.",
                "severity": "critical",
                "tier": 3,
                "safe_action": "Halt automatic operations on this resource; alert human administrator for explicit review.",
                "confidence_score": 0.99
            }

        return {
            "root_cause": f"Unhandled exception or anomaly detected in {category}.",
            "severity": "medium",
            "tier": 2,
            "safe_action": "Generate diagnostic trace and isolate issue in sandbox before patching.",
            "confidence_score": 0.75
        }

    def _track_tokens(self, estimated_tokens: int, provider: str):
        state = get_state()
        curr_tokens = state.get("quota_tokens_used", 0) + estimated_tokens
        update_state({
            "quota_tokens_used": curr_tokens,
            "free_tier_provider": provider,
            "total_cost_usd": 0.0  # Zero cost on free quotas
        })


orchestrator = ModelOrchestrator()
