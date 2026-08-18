# ADR-002 OpenCode 集成方式：ACP adapter（acpx 插件）

> 状态：已接受　类型：技术选型　日期：2026-08-12
> 架构阶段：环节 3（record_decisions）｜替代：旧 ADR-002（subprocess+--session，已废弃）

## 背景

OpenClaw 需调用本地 OpenCode 执行编程任务。候选：subprocess 直接调用 vs OpenClaw ACP adapter。

## 决策

- **主方案**：OpenClaw ACP 运行时插件 @openclaw/acpx，以 `agent=opencode`、`backend=acpx`、`mode=persistent` 声明式接入 OpenCode ACP server。
- **配置**：`~/.openclaw/openclaw.json` agents.list + bindings，cwd 指向项目根。
- **废弃**：自研 subprocess+--session 调用方案。

## 权衡

| 维度 | ACP adapter（取） | subprocess+--session（弃） |
|------|--------------------|----------------------------|
| 协议 | ACP 官方协议 | 非标准 |
| 会话状态 | Gateway 托管 | 自研管理 |
| 持久化 | chat↔session 映射 | 需自研 |
| 与 OpenClaw 生态 | 原生集成 | 脱离 |

## 理由

opencode 1.17.4 原生支持 ACP server；acpx 为 OpenClaw 官方 ACP 运行时；persistent 模式满足会话延续；N-REQ-03 要求 ACP 适配。

## 影响

- 正向：声明式配置、会话托管、与 OpenClaw 一致
- 负向：依赖 acpx 插件与 ACP 协议稳定性（ARCH-RISK-102/103）
- 关联：N-REQ-02/03；IF-002/IF-003
