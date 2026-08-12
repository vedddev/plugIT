# analytics/tracker.py

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import logging
import uuid

from database.dashboard import record_request
from database.config import database_url as configured_database_url
from database.initialization import initialize_database


@dataclass
class RequestLog:

    request_id: str

    timestamp: str

    provider: str

    model: str

    prompt: str

    input_tokens: int

    output_tokens: int

    total_tokens: int

    latency_ms: float

    cost: float

    cached: bool

    success: bool


class AnalyticsTracker:

    def __init__(self, log_dir: str = "logs", database_url: str | None = None):

        self.log_dir = Path(log_dir)

        self.log_dir.mkdir(exist_ok=True)

        self.log_file = self.log_dir / "requests.jsonl"
        # Persist request lifecycle data by default for every SmartLLM instance,
        # including CLI callers that do not run the FastAPI lifespan hook.
        self.database_url: str | None = database_url or configured_database_url()
        try:
            initialize_database(self.database_url)
        except Exception:
            # Analytics persistence must not make an otherwise usable LLM
            # gateway unavailable. ``log`` retains the same non-fatal policy.
            logging.getLogger(__name__).exception("Failed to initialize request-event persistence")
            self.database_url = None

    def enable_database(self, database_url: str | None = None) -> None:
        """Enable application-database event persistence after startup."""
        selected_url = database_url or configured_database_url()
        try:
            initialize_database(selected_url)
        except Exception:
            logging.getLogger(__name__).exception("Failed to initialize request-event persistence")
            self.database_url = None
            return
        self.database_url = selected_url

    def log(
        self,
        *,
        provider: str,
        model: str,
        prompt: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        latency_ms: float,
        cost: float,
        cached: bool = False,
        success: bool = True,
        api_key_id: str = "anonymous",
    ):

        entry = RequestLog(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
            model=model,
            prompt=prompt,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost=cost,
            cached=cached,
            success=success,
        )

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)))
            f.write("\n")

        if self.database_url is not None:
            try:
                record_request(
                    api_key_id=api_key_id,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost=cost,
                    cached=cached,
                    success=success,
                    database_url=self.database_url,
                    created_at=entry.timestamp,
                )
            except Exception:
                logging.getLogger(__name__).exception("Failed to persist dashboard request event")
