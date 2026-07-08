from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional


class JobWorker:
    def __init__(self, handler: Optional[Callable[[str, Dict[str, Any]], None]] = None):
        self.handler = handler or self._default_handler

    def dispatch(self, job_id: str, payload: Dict[str, Any]) -> None:
        thread = threading.Thread(target=self._run_handler, args=(job_id, payload), daemon=True)
        thread.start()

    def _run_handler(self, job_id: str, payload: Dict[str, Any]) -> None:
        self.handler(job_id, payload)

    def _default_handler(self, job_id: str, payload: Dict[str, Any]) -> None:
        return None
