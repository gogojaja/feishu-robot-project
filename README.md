# Free API Hub — 飞书/Lark 机器人集成解决方案
用于移动端编程交互，实现飞书/Lark 平台与 AI 编程助手的无缝连接

## 项目概述

本项目实现了基于飞书/Lark 平台的移动端编程交互系统，允许用户通过飞书/Lark 与 AI 编程助手进行对话和编程操作。提供以下核心功能：

- **消息交互**：通过飞书/Lark 发送和接收消息
- **代码执行**：执行 Python 代码并返回结果
- **文件操作**：读取和写入文件
- **命令执行**：执行系统命令

## 技术架构

### 核心组件

1. **飞书/Lark 机器人** (`src/feishu_integration.py`)
   - Feishu/Lark 消息处理
   - 代码执行和文件操作
   - 完整的集成解决方案

2. **支持脚本**
   - `scripts/start-feishu.sh`：启动飞书机器人
   - `scripts/stop-feishu.sh`：停止飞书机器人
   - `scripts/test_feishu.py`：测试脚本

### 数据流

```
飞书/Lark 用户 → 飞书机器人 → AI 编程助手 → 模型响应 → 飞书/Lark 用户
```

## 安装与配置

### 1. 环境准备

确保您的系统满足以下要求：

- **操作系统**：macOS、Linux 或 Windows（支持 WSL2）
- **Python**：3.9 或更高版本
- **网络连接**：访问飞书开放平台 API

### 2. 安装 Python 依赖

```bash
# 安装项目依赖
cd /path/to/feishu-robot-project
pip install -r requirements.txt

# 安装飞书 SDK
pip install lark-oapi
```

### 3. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/) 并登录
2. 点击 "开发者后台" → "创建应用"
3. 填写应用信息，启用机器人能力
4. 获取应用凭证（App ID、App Secret）
5. 配置事件回调 URL：`http://127.0.0.1:5103/feishu/events`

### 4. 配置飞书应用

在 `config/feishu.yaml` 中配置应用凭证：

```yaml
# 应用 ID
app_id = "cli_your_app_id_here"

# 应用密钥
app_secret = "your_app_secret_here"

# 事件验证令牌（可选）
verification_token = "your_verification_token_here"
```

### 5. 启动飞书机器人

```bash
# 启动飞书机器人
cd /path/to/feishu-robot-project
bash scripts/start-feishu.sh
```

## 使用说明

### 1. 基本交互

用户可以通过飞书/Lark 与机器人进行对话：

- **发送文本消息**：直接发送文本，机器人将自动识别并响应
- **执行代码**：发送包含 ````python` 代码块的消息，机器人将执行代码
- **文件操作**：发送文件消息，机器人将读取文件内容

### 2. 示例对话

```
用户：你好，机器人！
机器人：我已收到您的消息。您可以请求我执行编程任务，例如：
- 执行 Python 代码
- 读取文件
- 写入文件
- 运行命令

用户：```python
print("Hello, World!")
```
机器人：执行结果:
```
输出:
Hello, World!
退出码: 0
```

用户：读取文件并显示内容
机器人：正在读取文件... (执行文件读取操作)
```

用户：```python
with open("test.txt", "w") as f:
    f.write("Hello, World!")
```
机器人：已写入 /path/to/feishu-robot-project/test.txt (15 字符)
```
```

用户：停止服务
机器人：服务已停止
```

### 3. 高级功能

#### 代码执行

机器人支持执行 Python 代码，包括：

- 基础语法（print、if、for、while 等）
- 文件操作（read、write、open 等）
- 模块导入（import os、import json 等）
- 函数定义和调用

#### 文件操作

机器人可以读取和写入文件，包括：

- 读取文本文件
- 写入文本文件
- 读取 JSON 文件
- 写入 JSON 文件

#### 命令执行

机器人可以执行系统命令，包括：

- 系统命令（ls、cat、rm 等）
- Python 命令
- 文件操作命令

## 管理与监控

### 1. 检查状态

```bash
# 检查飞书机器人状态
curl http://127.0.0.1:5103/health
```

### 2. 停止服务

```bash
# 停止飞书机器人
bash scripts/stop-feishu.sh
```

## 开发与调试

### 1. 日志

日志文件位于：

- 飞书机器人日志：`/var/log/feishu_bot.log`

### 2. 测试

运行测试套件：

```bash
cd /path/to/feishu-robot-project
python3 scripts/test_feishu.py
```

### 3. 调试

如果遇到问题，请检查：

1. 网络连接是否正常
2. 飞书应用凭证是否正确
3. 事件回调 URL 是否配置正确
4. 日志中是否有错误信息

## 安全与权限

### 1. 应用权限

飞书应用需要以下权限：

- `im:message`：读取消息
- `im:message:send_as_bot`：发送消息
- `drive:drive`：文档授权管理

### 2. 数据安全

- 所有消息内容都会记录在日志中
- 确保在生产环境中配置正确的网络安全措施
- 定期检查日志以发现异常活动

## 常见问题

### 1. "飞书机器人无法启动"

检查：
- 网络连接是否正常
- 飞书应用凭证是否正确
- 端口 5103 是否已被占用

### 2. "消息发送失败"

检查：
- 租户访问令牌是否有效
- 网络连接是否正常
- 飞书应用权限是否正确

### 3. "代码执行失败"

检查：
- 代码语法是否正确
- 文件路径是否正确
- 系统权限是否足够

## 版本与更新

### 当前版本

- 版本：v1.0
- 更新日期：2026-06-15
- 更新内容：简化架构，优化代码结构

### 更新日志

- **2026-06-14**：初始版本，飞书/Lark 机器人集成
- **2026-06-15**：简化架构，优化代码结构
- **2026-06-16**：更新文档和脚本

## 许可

本项目采用 MIT 许可。您可以自由使用、修改和分发本项目，但需保留版权声明。

## 联系我们

如果您有任何问题或建议，请联系我们：

- 邮箱：support@free-api-hub.com

---

*本文档由飞书/Lark 机器人集成系统自动生成*