# POC 验证计划 — 飞书+OpenClaw+OpenCode（v0.3）

> 依据：review.md 环节 2（validate_prototype）· 版本：v0.3　日期：2026-08-12

## 1. 目标

验证 OpenClaw 路线架构关键假设（ADR-001~005）在 test 环境下的真实可用性，降低技术风险。

## 2. 验证范围与用例

| # | 验证项 | 对应决策/风险 | 方法 | 通过标准 |
|---|--------|--------------|------|----------|
| P1 | OpenClaw 版本与 Gateway 常驻 | ADR-004 / N-REQ-09 | openclaw --version + gateway status | 2026.7.1-2 + runtime running(pid 4639) |
| P2 | feishu 渠道插件加载 | ADR-001 / N-REQ-01 | plugins list + 日志 | feishu enabled + client ready |
| P3 | 飞书长连接建立 | ADR-001 / N-REQ-01 | 日志 websocket | ws client ready + bot open_id 解析 |
| P4 | ACP 运行时插件 acpx | ADR-002 / N-REQ-03 | plugins list + 日志 | acpx enabled + runtime pre-warmed |
| P5 | ACP 配置完整性 | ADR-002 / N-REQ-02 | openclaw.json 解析 | acp.enabled/agents.list/bindings 正确 |
| P6 | ACP 会话 smoke test | ADR-002 / N-REQ-03 | openclaw acp 正确消息格式 | 会话建立并返回输出 |
| P7 | 群绑定路由 | ADR-002 / N-REQ-02 | bindings 配置核验 | 单群 oc_7e3442d95ddf0b3c226cb528a4db2ced |
| P8 | 凭证权限 | ADR-005 / N-REQ-10 | 权限检查 | 配置 0600 + 不入仓库 |

## 3. 资源与环境

- 环境：test（.env_type=test）；OpenClaw 2026.7.1-2；opencode 1.17.4
- 配置：~/.openclaw/openclaw.json
- 约束：不修改任何存量文件；测试临时进程用后清理

## 4. 验证顺序

P1 → P2 → P3 → P4 → P5 → P6（核心风险）→ P7 → P8

## 5. 退出标准

- 全部 P1-P8 执行并记录结果
- 核心风险（ACP 链路）确认可用或记录明确限制与修复路径
- 输出 POC 验证报告.md
