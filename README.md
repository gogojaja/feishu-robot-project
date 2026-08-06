# Free API Hub — 飞书 → OpenCode 桥接服务

通过飞书/Lark 移动端或桌面端调用本机 OpenCode 进行编程开发，交互方式与终端使用 OpenCode 完全一致。

## 架构

```
飞书用户 → 飞书开放平台 → 本机 Flask 服务 → opencode run → AI 响应 → 飞书用户
```

**单文件架构**：`src/feishu_integration.py` 包含全部逻辑，无额外组件。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

### 1. 飞书应用配置

在 `config/feishu.yaml` 中填写飞书应用凭证：

```yaml
app_id = "cli_xxx"
app_secret = "xxx"
verification_token = "xxx"
```

### 2. 飞书开放平台配置

- 创建应用并启用机器人能力
- 事件回调 URL: `http://公网IP或内网穿透地址:5103/feishu/events`
- 权限: `im:message`, `im:message:send_as_bot`

### 3. 网络配置（内网穿透）

飞书需要公网可访问的回调地址。推荐使用：
- [frp](https://github.com/fatedier/frp)
- [ngrok](https://ngrok.com)
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

## 启动

```bash
bash scripts/start-feishu.sh
```

## 验证

```bash
curl http://127.0.0.1:5103/health
python3 scripts/test_feishu.py
```

## 停止

```bash
bash scripts/stop-feishu.sh
```

## 使用方式

在飞书中向机器人发送任意文字消息，OpenCode 会处理并返回结果，与终端使用体验一致。

## 文件说明

| 文件 | 作用 |
|------|------|
| `src/feishu_integration.py` | 核心服务，接收飞书消息并转发给 OpenCode |
| `scripts/start-feishu.sh` | 启动脚本 |
| `scripts/stop-feishu.sh` | 停止脚本 |
| `scripts/test_feishu.py` | 测试脚本 |
| `scripts/check_env.py` | 环境检查 |
| `config/feishu.yaml` | 飞书应用配置 |
| `AGENTS.md` | 项目沟通准则 |

## 已知问题

- `opencode run` 需清除 `OPENCODE_SERVER_PASSWORD` 环境变量（已在代码中自动处理）
- 飞书回调地址需公网可达
