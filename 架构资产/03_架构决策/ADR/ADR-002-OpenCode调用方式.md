# ADR-002 OpenCode 调用方式：subprocess + --session 会话复用（已废弃）

> 状态：已废弃（由 ADR-002-OpenCode集成方式.md 取代）　类型：技术选型　日期：2026-08-05
> 废弃原因：2026-08-12 架构重置，OpenCode 集成改由 OpenClaw ACP adapter（acpx）承载
> 架构阶段：环节 3（record_decisions）

## 背景

机器人需按 open_id 调用本机 OpenCode 完成编程任务并保持会话上下文连续。OpenCode 官方提供两种非交互调用路径：`opencode run --session` 子进程复用，与 `opencode serve`+`run --attach` 常驻 server。

## 决策

- **主方案**：`subprocess.run(["opencode","run",msg,"--format","json","--session",sid], timeout=180)`，每次独立子进程，按 open_id 映射 session_id 保持上下文。
- **会话映射**：`sessions[open_id] → opencode sessionID`（内存态）。

## 权衡

| 维度 | subprocess+--session（主） | serve+attach（备选） |
|------|----------------------------|----------------------|
| 常驻进程 | 无，用完即退 | 需常驻 server 进程 |
| 会话保持 | `--session <id>` 官方支持 | 通过 attach 复用 |
| 并发 | 单用户足够 | 多并发更强 |
| 复杂度 | 低（存量已实现） | 高（端口/生命周期管理） |

## 理由

- 官方 CLI 文档明确支持 `--continue`/`--session` 会话复用（opencode.ai/docs/cli）
- 存量代码已验证，零改动；单用户场景并发需求低
- 满足 REQ-FUNC-REQ-004（按 open_id 维护 session 上下文连续）

## 影响

- 正向：保持会话连续、超时控制明确（180s）
- 约束：每次调用有启动开销；进程重启上下文丢失（风险 ARCH-RISK-010）
- 关联：C8 OpenCodeRunner、组件设计文档 §3

## 引用

- OpenCode 官方 CLI 文档：opencode.ai/docs/cli
- 社区指南：grapeot/context-infrastructure（AI CLI Agent 指南）
