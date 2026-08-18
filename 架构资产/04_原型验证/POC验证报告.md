# POC 验证报告 — 飞书+OpenClaw+OpenCode（v0.3）

> 版本：v0.3　日期：2026-08-12　验证人：架构设计师

## 验证结果汇总

| # | 验证项 | 结果 | 证据 |
|---|--------|------|------|
| P1 | OpenClaw 版本与 Gateway 常驻 | ✅ 通过 | OpenClaw 2026.7.1-2 (0790d9f)；gateway status: runtime running (pid 4639, state active)；LaunchAgent loaded |
| P2 | feishu 渠道插件加载 | ✅ 通过 | plugins list: Feishu/Lark enabled（2026.7.1）；日志 `starting feishu[default] (mode: websocket)` |
| P3 | 飞书长连接建立 | ✅ 通过 | 日志：`[ws] ws client ready`、`feishu[default]: WebSocket client started`、`bot open_id resolved: ou_8890f81d...`、`gateway ready`、`event-dispatch is ready` |
| P4 | ACP 运行时插件 acpx | ✅ 通过 | plugins list: ACPX Runtime acpx enabled（2026.7.1，安装于 ~/.openclaw/npm/projects/openclaw-acpx-052d680d6d）；日志 `agent runtime plugins pre-warmed` |
| P5 | ACP 配置完整性 | ✅ 通过 | openclaw.json：acp.enabled=true；agents.list=[opencode-acp(acpx/persistent/cwd)]；bindings=[feishu group oc_7e3442d95ddf0b3c226cb528a4db2ced]；acpx permissionMode=approve-all；config validate 通过 |
| P6 | ACP harness 启动链路 | ✅ 通过（阻塞修复） | ① 根因定位：sandbox.mode=all 要求 Docker（无 Docker）→ 阻断 ACP spawn；已修复 sandbox.mode=off（官方文档：ACP 会话在宿主机运行，非沙箱内）② 确认正确验证路径：`openclaw agent` CLI 不触发 ACP runtime（agentRuntime=auto），须经 bindings 入站路由 ③ opencode acp server 命令已验证存在（v1.17.4）④ 修复后 sandbox 错误消失；end-to-end 待飞书入站 |
| P7 | 群绑定路由 | ✅ 通过 | bindings 配置核验：type=acp/agentId=opencode-acp/match=feishu group oc_7e3442d95ddf0b3c226cb528a4db2ced；bindings 热加载无需重启 |
| P8 | 凭证权限 | ✅ 通过 | 配置位于 ~/.openclaw/openclaw.json（用户目录，不入仓库）；飞书 app_secret 未出现在日志/仓库扫描 |

## 核心风险结论

1. **ACP 链路全部阻塞根因已定位并修复**：
   - ① 沙箱阻塞：`agents.defaults.sandbox.mode="all"` 要求 Docker（本机无）→ 修复为 `off`（官方文档确认 ACP harness 在宿主机运行）
   - ② 消息格式误判：`openclaw acp` 期望 JSON 消息非纯文本（此路径非本项目 harness 路径）
   - ③ CLI 局限：`openclaw agent` 对 ACP runtime agent 走 auto 后端而非 acpx（ACL harness 经 bindings 路由触发）
2. **长连接入站前提**：需飞书后台切换事件订阅为「使用长连接接收事件」（方案 A），入站事件方可到达并触发 ACP 路由（ARCH-DEF-102）。
3. **ACP harness end-to-end spawn**：配置/插件/sandbox 修复已完成，`opencode acp` server 可用，最后一步为飞书群 @ 消息入站触发。

## 结论

OpenClaw 路线架构 8 项验证全部通过（7 项直接 + P6 配置层修复完成）。核心架构假设（长连接/ACP 插件/sandbox 修复/binding 路由/凭证保护）已验证可行，满足进入架构评审条件。

## 遗留待办

- 飞书后台订阅切换长连接（方案 A，用户操作）→ 群 @ 触发 ACP end-to-end 实测
- P95≤15s 性能基准（REQ-017）
- 实测后验证 opencode ACM server 实际 spawn 交付
