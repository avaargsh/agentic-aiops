# Agentic AIOps

证据优先（Evidence-first）的 Agentic 事件调研与安全修复参考实现，内含可运行的 **Golden Incident v0.1**，覆盖 Prometheus、Kubernetes、Decision Gateway 和 Temporal 持久审批。

## 什么是本项目

大模型擅长生成“看起来合理”的根因分析（RCA），但把流畅的 RCA 当作证据在 AIOps 中是危险的。本项目把调研与修复拆成六层边界：

1. **观察** — 原始或规范化的事实；
2. **假设** — 拟议的解释；
3. **验证** — 支持或反驳假设的证据；
4. **决策** — 接下来做什么；
5. **授权** — 该动作是否可以执行；
6. **事后验证** — 动作是否真的让系统恢复。

核心边界刻意设定为：**模型提出；确定性策略授权；Temporal 拥有持久生命周期；执行器执行有界写入；可观测性验证事件是否真的恢复。**

## Golden Incident v0.1

首个可运行的垂直切片演示 `checkout-api` 服务延迟超 SLO 的完整处置流程：

```text
Load / Alert
    ↓
Prometheus + Kubernetes 只读调研
    ↓
不可变证据包 + SHA-256
    ↓
Decision Gateway (/decision)
    ↓
确定性策略
    ↓
Temporal WAIT_APPROVAL
    │
    └── approval_resolved(approval_id)
              ↓
       Kubernetes scale 2 → 4
              ↓
       rollout 就绪
              ↓
       Prometheus 事后验证
       ┌────┴────┐
    VERIFIED   rollback
              ↓
       Temporal COMPLETE
              ↓
       证据引用 / 回放
```

### 复现演示

创建可丢弃的 Kubernetes 环境：

```bash
./scripts/setup-golden-kind.sh
```

使用 `compose.golden.yml` 启动 Temporal / Decision 支撑服务，然后运行事件入口：

```bash
./scripts/run-live-golden-incident.sh
```

启动命令在 Run 达到持久审批点后返回控制权。查询冻结的 Decision 以获取精确的待批准 ID：

```bash
python examples/live_golden_incident.py status \
  --run-id golden-checkout-live-001
```

然后批准该精确 ID：

```bash
golden-approval approve \
  --run-id golden-checkout-live-001 \
  --approval-id <pending_approval_id> \
  --reason "scale checkout-api"
```

对另一个动作的批准不授权本 Run 的冻结动作。

继续同一个 Run：

```bash
python examples/live_golden_incident.py continue \
  --run-id golden-checkout-live-001
```

录制路径见 `docs/golden-incident-v0.1.md`，四仓库拓扑见 `docs/golden-stack.md`。

### 验证录制应当显示的内容

```text
[ALERT]         checkout-api 延迟高于 SLO
[INVESTIGATE]   Prometheus + Kubernetes 只读证据
[EVIDENCE]      evidence://sha256/<bundle>
[DECISION]      执行 / scale deployment/checkout-api
[GOVERN]        WAIT_APPROVAL（不做任何 Kubernetes 写入）
[APPROVAL]      精确冻结动作 approval_id 被批准
[ACTION]        副本 2 -> 4；rollout 就绪
[VERIFY]        事后延迟 <= SLO
[COMPLETE]      Temporal Run 终止；证据引用已附加
[REPLAY]        冻结 bundle -> 相同决策；无实时读取
```

这是验收抄录，而非预先录制的成功声明：真实运行必须先产生相应状态，才能将演示描述为端到端验证。

## 安全与正确性属性

- 证据在假设和决策之前收集。
- 调研工具为只读；写入能力由独立执行器持有。
- 模型决策永远不会绕过确定性授权。
- 审批使用与动作绑定的稳定 `approval_id`；无关的审批不能授权冻结动作，Temporal 拥有信号去重。
- 部署 `authority_digest` 冻结到证据、决策、OperationRecord 和发布证据中；`authority` 漂移会在有界写入前使恢复失效。
- AIOps 流程在等待人工审批时不轮询。
- 成功的 `kubectl scale` 不等同于恢复：Prometheus 必须验证事后 SLO。
- 验证失败可以触发回滚。
- 冻结证据包支持不查询实时 Prometheus/Kubernetes 的确定性回放。

## 仓库角色

本仓库是参考栈中的 **证据生产者 + 动作编排层**，与以下仓库集成：

- [`agent-decision-lab`](https://github.com/avaargsh/agent-decision-lab) — 同步决策平面 `/decision` 边界。
- [`cloud-agent-runtime`](https://github.com/avaargsh/cloud-agent-runtime) — Temporal 支撑的持久 Run 生命周期与审批信号。
- [`agent-control-plane`](https://github.com/avaargsh/agent-control-plane) — AgentRelease 分辨、证据验证与发布推广门禁。

四者共同实现：

```text
Observe → Evidence → Decide → Govern → Durable Run → Act → Verify → Release Gate → Replay
```

## M1 实时软件验收基线

M1 实时软件验收在钉住的公共 mainline 提交上验证：新建 kind + Temporal 运行产生 `PROMOTE`，同一 authority 下的变异证据产生带 `INVALID_RELEASE_EVIDENCE` 的 `BLOCK`。确切修订版、推送 CI 和证明工件见 [冻结 M1 基线](docs/baselines/m1-public-mainline.md)。这证明了参考软件切片，但不等同于建立生产 SLO 或真实 GPU 性能。

## v0.1 之后的范围

参考切片故意保持窄：Kubernetes 工作负载降级与有界 scale 修复。未来实验可以覆盖 GPU/NCCL/RDMA 事件、错误预算烧耗与变更回归，而无需改变此处演示的控制面边界。

## 核心模块与设计

| 模块 | 职责 |
| --- | --- |
| `bundle.py` | `EvidenceBundle`：事件、证据、假设、拓扑实体/边、变更事件、元数据；内容寻址，通过 `sha256()` 计算不可变摘要 |
| `policy.py` | `ActionPolicy`：确定性动作门禁，按动作类型、爆炸半径、是否可回滚返回允许/需审批/拒绝 |
| `investigation.py` | 从冻结证据包重建调研状态（`investigation_from_bundle()`），支持回放 |
| `prometheus_tool.py` / `kubernetes_tool.py` | 只读 HTTP 观测适配器（PromQL 查询、K8s 资源列表），不发送 POST/PUT/PATCH/DELETE |
| `durable_incident.py` / `temporal_*.py` | Temporal 持久工作流：WAIT_APPROVAL、信号去重、审批恢复 |
| `remediation.py` / `action_orchestrator.py` | 有界修复执行与动作编排 |
| `evaluation.py` / `release_metrics.py` | 回放评估：未支撑主张率、错误自动化率、升级准确率、多余工具率、恢复成功率 |
| `cli.py` | `agentic-aiops evaluate-scenarios`：对冻结场景进行回放评估并输出度量 |
| `approval_cli.py` | `golden-approval`：对精确 `approval_id` 批准/拒绝 |

审批边界采用鸭子类型 `ApprovalSink` 桥接（`request_approval(run_id, action, evidence_refs)`），本仓库不直接导入 `cloud-agent-runtime`，使运行时可替换而安全边界保持不变。审批记录（Decision Ledger）只记录对外有意义的事实：选定的有界路径、确定性策略原因、证据 ID、是否需要审批、目标/爆炸半径、审批引用；模型隐藏推理不作为审计来源。

## 四仓库金色栈与可执行验收

将以下仓库作为兄弟目录保持：

```text
workspace/
├── agent-control-plane/
├── cloud-agent-runtime/
├── agent-decision-lab/
└── agentic-aiops/
```

启动轻量级集成拓扑：

```bash
docker compose -f compose.golden.yml --profile demo up --build
```

该栈启动 Temporal、Cloud Agent Runtime 工作器、Decision Gateway 和金色事件演示容器。

可执行验收（`make acceptance-build` / `make acceptance`）的预期终端输出：

```text
[5/5] PASS
release=checkout-sre-golden-v1
run_id=golden-checkout-acceptance-001
gate=PROMOTE
```

验收由三个持久工件支撑（`.golden-runs/<run-id>/`）：`post-action-evidence.json`、`release-evidence.json`、`acceptance-metrics.json`。控制平面是推广的最终权威；成功的 Kubernetes 写入不足以通过，证据缺失/变更、验证失败、缺少度量或门禁失败都会阻止推送。

## 依赖锁

跨仓库依赖修订版由机器可读的 [`stack.lock.json`](stack.lock.json) 拥有，不重复在工作流 YAML 中。本地验证：

```bash
make stack-lock-check
# 或安装后
agent-stack-lock stack.lock.json
```

栈变更因此成为显式可评审的依赖更新；CI 会在需要的仓库被重命名、修订版不是完整提交 SHA、或正/负发布门禁合约被意外更改时失败并拒绝。

## 开发

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

命令行工具：

- `agentic-aiops evaluate-scenarios <场景文件...>` — 回放评估
- `golden-approval approve/deny ...` — 事件审批
- `agent-stack-lock stack.lock.json` — 依赖锁校验

跨仓库集成由 `.github/workflows/four-repo-acceptance.yml` 验证：从本仓库的主推送 CI 钉住公共控制平面、运行时和决策提交，在可丢弃的 kind + Temporal 基础设施上运行。

## 贡献与许可

欢迎通过聚焦的议题和拉取请求贡献。参见 `CONTRIBUTING.md`、`SECURITY.md` 和 `CODE_OF_CONDUCT.md`。

采用 Apache License 2.0 授权。参见 `LICENSE`。

---

> **语言说明**：GitHub 会根据访问者的语言偏好自动展示对应语言的 README。中文用户默认看到本文件（`README.zh-CN.md`）；英文原文保留在 `README.md`。
