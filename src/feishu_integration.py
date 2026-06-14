"""
模块名称：feishu_integration
功能描述：Feishu/Lark 机器人集成模块，实现移动端编程交互
对外接口：
    - FeishuBot：Feishu/Lark 机器人主类
    - setup_feishu_app：创建飞书应用
    - handle_message：消息处理
依赖：
    - 标准库：os, sys, json, logging, threading, subprocess, tempfile, pathlib, datetime, urllib.parse
    - 第三方：requests, flask
    - 项目内：shared.feishu_api, assistants.chat-assistant.src.main (talk, search), assistants.office-assistant.src.core (WordProcessor, ExcelProcessor, DocumentSummarizer), assistants.life-assistant.src.scheduler, assistants.file-assistant.src.file_manager, assistants.sys-assistant.src.system_monitor
版本：v1.0
更新记录：
    - 2026-06-14: 初始创建，实现飞书机器人集成
    - 2026-06-15: 简化架构，优化代码结构
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any
import requests
from flask import Flask, request, jsonify

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger("FeishuBot")


class FeishuBot:
    """
    模块名称：feishu_integration
    功能描述：Feishu/Lark 机器人集成模块，实现移动端编程交互
    对外接口：
        - FeishuBot：Feishu/Lark 机器人主类
        - setup_feishu_app：创建飞书应用
        - handle_message：消息处理
    依赖：
        - 标准库：os, sys, json, logging, threading, subprocess, tempfile, pathlib, datetime, urllib.parse
        - 第三方：requests, flask
        - 项目内：shared.feishu_api, assistants.chat-assistant.src.main (talk, search), assistants.office-assistant.src.core (WordProcessor, ExcelProcessor, DocumentSummarizer), assistants.life-assistant.src.scheduler, assistants.file-assistant.src.file_manager, assistants.sys-assistant.src.system_monitor
    版本：v1.0
    更新记录：
        - 2026-06-14: 初始创建，实现飞书机器人集成
        - 2026-06-15: 简化架构，优化代码结构
    """

    def __init__(self, app_id: str, app_secret: str, verification_token: str = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.tenant_access_token = None
        self.token_expire_time = 0
        self.setup_logging()
        self.get_tenant_access_token()

    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    def get_tenant_access_token(self):
        """获取租户访问令牌"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    self.tenant_access_token = result["tenant_access_token"]
                    self.token_expire_time = int(time.time()) + 7200
                    logger.info("租户访问令牌获取成功")
                    return True
                else:
                    logger.error(f"获取令牌失败: {result}")
            else:
                logger.error(f"HTTP 请求失败: {resp.status_code}")
        except Exception as e:
            logger.error(f"获取令牌异常: {e}")
        return False

    def send_message(self, receive_id: str, content: str, msg_type: str = "text"):
        """发送消息"""
        if not self.tenant_access_token or int(time.time()) > self.token_expire_time:
            self.get_tenant_access_token()

        url = f"https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.tenant_access_token}"
        }
        data = {
            "receive_id": receive_id,
            "content": content,
            "msg_type": msg_type
        }

        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    logger.info(f"消息发送成功，接收者: {receive_id}")
                    return True
                else:
                    logger.error(f"消息发送失败: {result}")
            else:
                logger.error(f"HTTP 请求失败: {resp.status_code}")
        except Exception as e:
            logger.error(f"发送消息异常: {e}")
        return False

    def handle_message(self, event_data: Dict[str, Any]):
        """处理消息事件"""
        try:
            event = event_data.get("event", {})
            sender = event.get("sender", {})
            message = event.get("message", {})
            chat_id = event.get("chat_id")

            sender_type = sender.get("sender_type")
            sender_id = sender.get("sender_id", {}).get("open_id")
            msg_type = message.get("message_type")
            content = message.get("content")

            logger.info(f"收到消息 - 发送者: {sender_id}, 类型: {msg_type}")

            if msg_type == "text":
                self.process_text_message(sender_id, chat_id, content)
            elif msg_type == "image":
                self.send_message(sender_id, "我已收到图片消息。请问您需要什么帮助？")
            elif msg_type == "file":
                self.send_message(sender_id, "我已收到文件消息。您可以请求我读取文件内容。")
            else:
                self.send_message(sender_id, f"不支持的消息类型: {msg_type}")

        except Exception as e:
            logger.error(f"处理消息异常: {e}")

    def process_text_message(self, sender_id: str, chat_id: str, content: str):
        """处理文本消息"""
        try:
            content_dict = json.loads(content)
            text = content_dict.get("text", "")
        except json.JSONDecodeError:
            text = content

        if self.is_code_request(text):
            self.process_code_request(sender_id, text)
        else:
            self.send_message(
                sender_id,
                "我已收到您的消息。您可以请求我执行编程任务，例如：\n"
                "- 执行 Python 代码\n"
                "- 读取文件\n"
                "- 写入文件\n"
                "- 运行命令"
            )

    def is_code_request(self, text: str) -> bool:
        """检查是否为代码请求"""
        code_indicators = [
            "```python", "def ", "import ", "print(",
            "class ", "for ", "while ", "if ",
            "return ", "with open", "import os"
        ]
        return any(indicator in text for indicator in code_indicators)

    def process_code_request(self, sender_id: str, code: str):
        """处理代码请求"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_file = f.name

            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(BASE_DIR)
            )

            response = self.format_execution_result(result)
            self.send_message(sender_id, response)
            os.unlink(temp_file)

        except subprocess.TimeoutExpired:
            self.send_message(sender_id, "代码执行超时，请检查代码")
        except Exception as e:
            self.send_message(sender_id, f"执行失败: {e}")

    def format_execution_result(self, result: subprocess.CompletedProcess) -> str:
        """格式化执行结果"""
        response = "执行结果:\n```\n"
        if result.stdout:
            response += f"输出:\n{result.stdout}\n"
        if result.stderr:
            response += f"错误:\n{result.stderr}\n"
        response += f"退出码: {result.returncode}\n```\n"
        return response

    def start_server(self, port: int = 5103):
        """启动消息服务器"""
        app = Flask(__name__)

        @app.route("/feishu/events", methods=["POST"])
        def feishu_events():
            """飞书事件处理"""
            try:
                if self.verification_token:
                    token = request.headers.get("X-Lark-Request-Token")
                    if token != self.verification_token:
                        return jsonify({"error": "验证失败"}), 403

                event_data = request.get_json()
                if event_data:
                    self.handle_message(event_data)
                    return jsonify({"status": "ok"})
                else:
                    return jsonify({"error": "无效的事件数据"}), 400

            except Exception as e:
                logger.error(f"事件处理异常: {e}")
                return jsonify({"error": str(e)}), 500

        @app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok", "bot_ready": True})

        logger.info(f"飞书机器人服务器启动，端口: {port}")
        app.run(host="127.0.0.1", port=port, debug=False)


def setup_feishu_app():
    """
    创建飞书应用并返回配置
    """
    logger.info("正在创建飞书应用...")

    app_config = {
        "app_id": "cli_a1b2c3d4e5f6g7h8i9j0",
        "app_secret": "secret_example_1234567890abcdef",
        "verification_token": "token_example_1234567890abcdef",
        "webhook_url": "http://127.0.0.1:5103/feishu/events"
    }

    logger.info(f"飞书应用创建完成，App ID: {app_config['app_id']}")
    return app_config


def main():
    """主函数"""
    logger.info("启动飞书机器人集成...")

    app_config = setup_feishu_app()

    bot = FeishuBot(
        app_id=app_config["app_id"],
        app_secret=app_config["app_secret"],
        verification_token=app_config["verification_token"]
    )

    bot.start_server()


if __name__ == "__main__":
    import time
    main()
