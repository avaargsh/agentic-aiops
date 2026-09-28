from __future__ import annotations

import asyncio
import os

from cloud_agent_runtime import TemporalRunBridge, TemporalWorkflowDriver
from temporalio.client import Client

from .temporal_port import AsyncTemporalPortAdapter

def build_temporal_port(address: str | None = None, task_queue: str | None = None) -> AsyncTemporalPortAdapter:
    address = address or os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7233")
    task_queue = task_queue or os.environ.get("TEMPORAL_TASK_QUEUE", "agent-runs")
    loop = asyncio.new_event_loop()
    client = loop.run_until_complete(Client.connect(address))
    driver = TemporalWorkflowDriver(client=client, task_queue=task_queue)
    bridge = TemporalRunBridge(driver)
    return AsyncTemporalPortAdapter(bridge=bridge, run_async=loop.run_until_complete)
