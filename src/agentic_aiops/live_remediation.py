from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from .action_orchestrator import ProposedAction
from .http_client import JsonHttpClient
from .remediation import ExecutionResult, RollbackResult, VerificationResult


@dataclass
class KubectlScaleExecutor:
    namespace: str = "golden-demo"
    before_replicas: int = 2
    after_replicas: int = 4
    kubectl: str = "kubectl"

    def _run(self, *args: str) -> str:
        completed = subprocess.run([self.kubectl, *args], check=True, capture_output=True, text=True)
        return completed.stdout.strip()

    def execute(self, action: ProposedAction) -> ExecutionResult:
        if action.action_kind != "scale":
            raise ValueError(f"unsupported live action: {action.action_kind}")
        kind, _, name = action.target.partition("/")
        if kind.lower() != "deployment" or not name:
            raise ValueError(f"unsupported scale target: {action.target}")
        self._run("-n", self.namespace, "scale", "deployment", name, f"--replicas={self.after_replicas}")
        self._run("-n", self.namespace, "rollout", "status", "deployment", name, "--timeout=180s")
        observed = self._run("-n", self.namespace, "get", "deployment", name, "-o", "jsonpath={.status.readyReplicas}")
        return ExecutionResult(True, action.target, (f"k8s://{self.namespace}/{action.target}/ready-replicas/{observed}",))

    def rollback(self, action: ProposedAction, execution: ExecutionResult) -> RollbackResult:
        _, _, name = action.target.partition("/")
        self._run("-n", self.namespace, "scale", "deployment", name, f"--replicas={self.before_replicas}")
        self._run("-n", self.namespace, "rollout", "status", "deployment", name, "--timeout=180s")
        return RollbackResult(True, (f"k8s://{self.namespace}/{action.target}/rollback/{self.before_replicas}",))


@dataclass
class PrometheusPostActionVerifier:
    base_url: str
    latency_query: str = "max(checkout_request_latency_seconds)"
    max_latency_seconds: float = 0.35
    settle_seconds: float = 5.0
    sample_timeout_seconds: float = 15.0
    poll_interval_seconds: float = 1.0
    client: JsonHttpClient = JsonHttpClient()

    def verify(self, action: ProposedAction, execution: ExecutionResult) -> VerificationResult:
        if self.settle_seconds > 0:
            time.sleep(self.settle_seconds)

        url = self.base_url.rstrip("/") + "/api/v1/query?" + urlencode({"query": self.latency_query})
        deadline = time.monotonic() + max(0.0, self.sample_timeout_seconds)

        while True:
            payload = self.client.get_json(url)
            results = list(dict(payload.get("data") or {}).get("result") or [])
            if results:
                value = float(results[0]["value"][1])
                evidence = f"prometheus://query/{self.latency_query}/value/{value}"
                return VerificationResult(
                    value <= self.max_latency_seconds,
                    (evidence,),
                    f"post-action latency={value:.4f}s threshold={self.max_latency_seconds:.4f}s",
                )

            if time.monotonic() >= deadline:
                return VerificationResult(
                    False,
                    (),
                    f"Prometheus returned no post-action latency sample within {self.sample_timeout_seconds:.1f}s",
                )

            time.sleep(max(0.0, self.poll_interval_seconds))
