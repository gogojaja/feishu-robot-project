# feishu-robot-project — 飞书 → OpenClaw → OpenCode 智能助理

通过飞书/Lark 移动端或桌面端调用本机 OpenCode 进行编程开发，交互方式与终端使用 OpenCode 完全一致。

## 架构（ADR-001）

```
飞书用户 → 飞书开放平台 → OpenClaw Gateway(18789, feishu WebSocket 长连接) → acpx → opencode ACP → 飞书用户
```

- **主链路**：OpenClaw feishu 长连接免公网/免 ngrok
- **状态**：自研 Flask Webhook + ngrok 链路已按 ADR-001 **彻底废弃移除**（2026-08-18），仅保留在 `备份/废弃_webhook桥_20260818/`

## 环境检查

```bash
python3 scripts/check_env.py
```

- 验证 `.env_type` 为 `test`
- 验证废弃链路无残留（废弃代码文件 / 5102/5103 端口 / ngrok 进程）
- 验证 OpenClaw Gateway 18789 监听与 feishu 长连接渠道 running

## OpenClaw 配置

配置位于 `~/.openclaw/openclaw.json`（appId / appSecret / feishu accounts 等），涉及网关配置变更先备份再改，可用 `scripts/openclaw-gate-check.sh` 完成备份-校验-重启-验证四步。

## 使用方式

在飞书中向机器人发送任意文字消息，OpenClaw → opencode ACP 处理并返回结果，与终端使用体验一致。

## 停止/重启网关（必要时）

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway   # 重启
openclaw channels status                                  # 验证 feishu 渠道
```

## 文件说明

| 文件 | 作用 |
|------|------|
| `scripts/check_env.py` | 环境检查（含废弃链路残留阻断） |
| `scripts/openclaw-gate-check.sh` | OpenClaw 网关配置变更门禁（备份/校验/重启/验证） |
| `scripts/pre-commit-env-gate.sh` | git pre-commit 门禁（端口台账冲突 + 废弃链路引用阻断） |
| `AGENTS.md` | 项目沟通准则 |
| `架构事实基线.md` | 架构与环境事实权威基线 |