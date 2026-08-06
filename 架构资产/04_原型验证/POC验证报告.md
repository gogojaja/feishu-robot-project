# POC 验证报告 — 飞书机器人项目

> 依据：review.md 环节 2（validate_prototype）· 版本：v0.1　日期：2026-08-05

## 1. 执行摘要

| 结果 | 数量 |
|------|------|
| 通过 | 4 |
| 有条件通过 | 1 |
| 未通过/受限 | 1 |

**核心发现**：opencode CLI 存在且 serve 模式可启动，但 **`opencode run` 直调模式在当前环境报 "Session not found"**，attach 模式可建 session 但模型推理返回 UnknownError。该限制直接关联 ADR-002 的存量调用方式，需在开发阶段调整调用策略。

## 2. 用例执行结果

| # | 验证项 | 结果 | 证据 | 结论 |
|---|--------|------|------|------|
| P1 | 服务存活 | ✅ 通过 | `GET /health` → `{"status":"ok"}` | 可用性探针正常 |
| P2 | opencode CLI | ✅ 通过 | `opencode --version` → `1.17.4` | CLI 已安装且可执行 |
| P3 | 会话连续 | ⚠️ 有条件 | serve 启动成功；attach 返回 sessionID 但推理 UnknownError | 会话机制存在，推理链路受环境限制 |
| P4 | JSON 输出 | ✅ 通过 | `--format json` 输出 JSON Lines；`--print-logs` 可诊断 | 格式契约成立 |
| P5 | challenge 校验 | ✅ 通过（代码评审） | feishu_integration.py:171-172 url_verification 原样返回 | 符合飞书官方要求 |
| P6 | 环境变量清理 | ✅ 通过（代码评审） | feishu_integration.py:93-95 env.pop 两键 | 满足 REQ-FUNC-REQ-011 |

## 3. 关键技术发现（Spike）

### 3.1 `opencode run` 直调报错
- **现象**：`opencode run "..." --format json` 报 `Error: Session not found`
- **原因**：社区指南记载——opencode run 单独执行因内置 server 启动失败会报此错；正确用法是先起 headless server 再 `run --attach`
- **影响**：存量代码（feishu_integration.py:96）使用的直调模式在当前环境不可直接运行

### 3.2 attach 模式推理受限
- **现象**：serve 启动成功（`server listening on http://127.0.0.1:5101`），attach 可创建 sessionID，但模型调用返回 `UnknownError: Unexpected server error`
- **归属**：server 层（两种模型 deepseek/copilot 均报同样错误，排除单 provider 问题）
- **推测**：当前模型 provider（免费/实验模型）或本机网络环境不支持该 serve 推理链路

## 4. 风险登记更新

| 风险 | 影响 | 应对 |
|------|------|------|
| opencode 调用方式需调整（直调→serve+attach 或配置默认 server） | 高 | 开发阶段（M4）验证备选调用路径并改造 C8 OpenCodeRunner |
| 模型推理链路在当前环境受限 | 中 | 明确 test 环境模型可达性；如受限则优先验证现有运行态 bot 的真实调用记录 |

## 5. T1 spike 补充结论（2026-08-06 M4 开发阶段）

### 5.1 验证结果

| 项目 | 结果 | 证据 |
|------|------|------|
| serve+attach 调用链路 | ✅ 端到端通过 | `opencode serve`（5102）→ `opencode run --attach` → free 模型返回真实文本 |
| free 模型推理 | ✅ 通过 | `opencode/deepseek-v4-flash-free` 返回 `"Hi! How can I help you..."`（11002 tokens） |
| volcark/volcark2 provider | ❌ 欠费 | `AccountOverdueError`（403）——账户余额逾期，非代码问题 |

### 5.2 根因定位（ARCH-DEF-001/002）

- **ARCH-DEF-001（直调 Session not found）**：`opencode run` 直调内置 server 启动失败所致，正确用法为 serve 常驻 + `run --attach`，与社区指南一致
- **ARCH-DEF-002（attach 推理 UnknownError）**：**真实根因 = 本地 opencode DB schema 半迁移**（`/Users/gogo/.local/share/opencode/opencode.db` 缺 `replacement_seq` 列，`SQLiteError`）。指向全新空库（`OPENCODE_DB`）后该错误消失，推理正常。**排除模型/provider 归属**

### 5.3 C8 调用策略定案

```bash
opencode serve --port 5102 --hostname 127.0.0.1   # 常驻服务（独立 DB）
opencode run "<msg>" --format json --model opencode/deepseek-v4-flash-free --attach http://127.0.0.1:5102 --session <sid>
```

- 模型：`opencode/deepseek-v4-flash-free`（免费可用，火山账户欠费不影响）
- 会话：`--session <sid>` 保持连续对话
- 数据库：独立 DB（避免全局 585MB 主库 schema 问题）

## 6. 最终结论

1. **架构骨架有效**：Flask 服务/健康检查/challenge/JSON 契约/环境清理均验证通过
2. **C8 调用方式定案**：serve 常驻 + attach + free 模型 + 独立 DB（见 §5.3），M4 T1 已闭环
3. **剩余风险**：volcark 火山账户欠费待充值；models.dev 拉取超时（不影响本地模型推理）
4. **ARCH-DEF-001/002 已根因定位**，代码层面无阻塞，可实施 C8 改造
