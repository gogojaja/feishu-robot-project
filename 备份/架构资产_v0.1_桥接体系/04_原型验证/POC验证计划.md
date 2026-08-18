# POC 验证计划 — 飞书机器人项目

> 依据：review.md 环节 2（validate_prototype）· 版本：v0.1　日期：2026-08-05

## 1. 目标

验证架构关键假设（ADR-001~005）在 test 环境下的真实可用性，降低技术风险。

## 2. 验证范围与用例

| # | 验证项 | 对应决策/风险 | 方法 | 通过标准 |
|---|--------|--------------|------|----------|
| P1 | 服务存活与健康检查 | ADR-004 / REQ-NFR-REQ-001 | curl /health | {"status":"ok"} |
| P2 | opencode CLI 可用性 | ADR-002 / REQ-FUNC-REQ-002 | opencode --version | 版本 v1.17.4 |
| P3 | opencode 会话连续（--session） | ADR-002 / REQ-FUNC-REQ-004 | opencode run + attach | sessionID 返回且可复用 |
| P4 | JSON 输出格式解析 | REQ-FUNC-REQ-008 | opencode --format json | 逐行 JSON、type=text |
| P5 | 事件回调 challenge 校验 | ADR-001 / REQ-FUNC-REQ-001 | 模拟 url_verification | challenge 原样返回 |
| P6 | 环境变量清理 | REQ-FUNC-REQ-011 | env.pop 检查 | 无 SERVER_PASSWORD |

## 3. 资源与环境

- 环境：test（.env_type=test）；端口 5103（服务）；5101（临时 serve）
- 工具：curl、opencode CLI v1.17.4
- 约束：不修改任何存量文件；测试临时进程用后清理

## 4. 验证顺序

P1 → P2 → P3/P4（核心风险）→ P5（代码评审确认）→ P6（代码评审确认）

## 5. 退出标准

- 全部 P1-P6 执行并记录结果
- 核心风险（opencode 调用）确认可用或记录明确限制
- 输出 POC 验证报告.md
