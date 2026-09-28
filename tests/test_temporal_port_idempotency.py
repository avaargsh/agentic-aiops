from agentic_aiops.temporal_port import AsyncTemporalPortAdapter

class Driver:
    def __init__(self): self.signals=[]
    async def signal(self, run, *, name, payload): self.signals.append((name,payload))

class Bridge:
    def __init__(self): self.driver=Driver(); self.approvals=[]
    async def signal_approval(self, run, *, approval_id, approved, evidence_refs=(), reason=None):
        self.approvals.append((approval_id,approved,tuple(evidence_refs),reason))

def sync(awaitable):
    import asyncio
    return asyncio.run(awaitable)

def test_adapter_preserves_stable_approval_id_for_temporal_deduplication():
    bridge=Bridge(); port=AsyncTemporalPortAdapter(bridge=bridge,run_async=sync)
    port.resolve_approval("run",approval_id="approval-001",approved=True,evidence_refs=("evidence://sha256/a",))
    port.resolve_approval("run",approval_id="approval-001",approved=True,evidence_refs=("evidence://sha256/a",))
    assert [item[0] for item in bridge.approvals] == ["approval-001","approval-001"]
    assert [name for name,_ in bridge.driver.signals] == ["resume_run","resume_run"]
