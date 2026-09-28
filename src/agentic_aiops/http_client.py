from __future__ import annotations

import json
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass(frozen=True)
class JsonHttpClient:
    bearer_token: str | None = None
    ca_file: str | None = None
    timeout_seconds: float = 5.0

    def get_json(self, url: str) -> dict[str, Any]:
        headers = {
            "accept": "application/json",
        }
        if self.bearer_token:
            headers["authorization"] = (
                f"Bearer {self.bearer_token}"
            )

        req = request.Request(
            url,
            headers=headers,
            method="GET",
        )

        context = ssl.create_default_context(
            cafile=self.ca_file
        )

        with request.urlopen(
            req,
            timeout=self.timeout_seconds,
            context=context,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )
