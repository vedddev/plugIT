# analytics/tracker.py

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import uuid


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

    def __init__(self, log_dir: str = "logs"):

        self.log_dir = Path(log_dir)

        self.log_dir.mkdir(exist_ok=True)

        self.log_file = self.log_dir / "requests.jsonl"

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