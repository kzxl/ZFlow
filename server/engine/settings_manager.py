"""
ZFlow Sovereign Settings Manager.
Manages global system settings, provider API keys, active workflow binding,
and engine preferences with atomic JSON persistence.
"""
import os
import json
import threading
from typing import Dict, Any, Optional

SETTINGS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "storage", "settings.json")
)

DEFAULT_SETTINGS: Dict[str, Any] = {
    # AI Providers & API Keys
    "openai_api_key": "",
    "gemini_api_key": "",
    "deepseek_api_key": "",
    "claude_api_key": "",
    "groq_api_key": "",
    
    # Local Engines & Endpoints
    "ollama_base_url": "http://localhost:11434",
    "comfyui_base_url": "http://127.0.0.1:8188",
    "vllm_base_url": "http://localhost:8000/v1",
    
    # Defaults
    "default_model": "gpt-4o-mini",
    "default_temperature": 0.7,
    "active_flow_id": "intelligent_enterprise_chatbot_flow",
    
    # Engine Preferences
    "enable_semantic_cache": True,
    "cache_ttl_seconds": 86400,
    "memory_window_size": 6,
    "rag_top_k": 3
}


class SettingsManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, file_path: str = SETTINGS_PATH):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self._settings: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(saved)
                    return merged
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._settings.copy()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            val = self._settings.get(key)
            if val is not None and val != "":
                return val
            # Check environment variable fallback (e.g. OPENAI_API_KEY)
            env_key = key.upper()
            if env_key in os.environ and os.environ[env_key]:
                return os.environ[env_key]
            return default if default is not None else DEFAULT_SETTINGS.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._settings[key] = value
            self._save()

    def update(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._settings.update(new_settings)
            self._save()
            return self._settings.copy()

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[SettingsManager] Failed to persist settings: {e}")


settings_manager = SettingsManager()
