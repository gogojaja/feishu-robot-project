"""
模块名称：feishu_test
功能描述：Feishu/Lark 机器人集成测试脚本
对外接口：
    - test_feishu_integration：测试飞书集成功能
    - test_message_handling：测试消息处理
    - test_opencode_bridge：测试 OpenCode 桥接功能
依赖：
    - 标准库：os, sys, json, logging, subprocess, tempfile, pathlib, datetime, urllib.parse
    - 第三方：requests, flask
    - 项目内：shared.feishu_api, assistants.chat-assistant.src.main (talk, search), assistants.office-assistant.src.core (WordProcessor, ExcelProcessor, DocumentSummarizer), assistants.life-assistant.src.scheduler, assistants.file-assistant.src.file_manager, assistants.sys-assistant.src.system_monitor
版本：v1.0
更新记录：
    - 2026-06-14: 初始创建，提供测试用例
    - 2026-06-15: 更新测试脚本，匹配 OpenCode 桥接架构
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import requests

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

logger = logging.getLogger("FeishuTest")


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def test_feishu_integration():
    """测试飞书集成功能"""
    print("=" * 60)
    print("测试飞书/Lark 机器人集成")
    print("=" * 60)

    # 测试 1：检查文件是否存在
    print("\n1. 检查文件结构...")
    required_files = [
        "src/feishu_integration.py",
        "scripts/start-feishu.sh",
        "scripts/stop-feishu.sh",
        "config/feishu.yaml"
    ]

    for file_path in required_files:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 文件不存在")

    # 测试 2：检查 Python 语法
    print("\n2. 检查 Python 语法...")
    try:
        import src.feishu_integration
        print("  ✅ Python 语法正确")
    except SyntaxError as e:
        print(f"  ❌ Python 语法错误: {e}")
    except ImportError as e:
        print(f"  ⚠️  导入错误: {e}")

    # 测试 3：检查环境变量
    print("\n3. 检查环境变量...")
    env_vars = [
        "FEISHU_APP_ID",
        "FEISHU_APP_SECRET",
        "FEISHU_VERIFICATION_TOKEN"
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var} = {value[:20]}...")
        else:
            print(f"  ⚠️  {var} 未设置")

    # 测试 4：检查端口占用
    print("\n4. 检查端口占用...")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5103))
        sock.close()
        if result == 0:
            print("  ⚠️  端口 5103 已被占用")
        else:
            print("  ✅ 端口 5103 可用")
    except Exception as e:
        print(f"  ❌ 端口检查失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def test_message_handling():
    """测试消息处理"""
    print("\n" + "=" * 60)
    print("测试消息处理")
    print("=" * 60)

    # 创建测试消息
    test_messages = [
        {
            "event": {
                "sender": {
                    "sender_type": "user",
                    "sender_id": {"open_id": "user123"}
                },
                "message": {
                    "message_type": "text",
                    "content": '{"text": "你好，机器人！"}'
                },
                "chat_id": "chat123"
            }
        },
        {
            "event": {
                "sender": {
                    "sender_type": "user",
                    "sender_id": {"open_id": "user456"}
                },
                "message": {
                    "message_type": "text",
                    "content": '```python\nprint("Hello, World!")\n```'
                },
                "chat_id": "chat456"
            }
        }
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. 测试消息 {i}:")
        print(f"   发送者: {message['event']['sender']['sender_id']['open_id']}")
        print(f"   类型: {message['event']['message']['message_type']}")
        print(f"   内容: {message['event']['message']['content']}")

    print("\n" + "=" * 60)
    print("消息处理测试完成")
    print("=" * 60)


def test_opencode_bridge():
    """测试 OpenCode 桥接功能"""
    print("\n" + "=" * 60)
    print("测试 OpenCode 桥接功能")
    print("=" * 60)

    test_messages = [
        "Hi",
        "list files in current directory",
        "what time is it?"
    ]

    for i, msg in enumerate(test_messages, 1):
        print(f"\n{i}. 发送消息: {msg}")
        try:
            env = os.environ.copy()
            env.pop("OPENCODE_SERVER_PASSWORD", None)
            env.pop("OPENCODE_SERVER_USERNAME", None)
            cmd = [
                "opencode", "run", msg, "--format", "json",
                "--model", "opencode/deepseek-v4-flash-free",
                "--attach", "http://127.0.0.1:5102",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(BASE_DIR),
                env=env
            )
            text_parts = []
            for line in (result.stdout or "").strip().split("\n"):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "text":
                        t = (obj.get("part") or {}).get("text", "")
                        if t:
                            text_parts.append(t)
                except json.JSONDecodeError:
                    pass
            response = "".join(text_parts)
            if response:
                import re
                clean = re.sub(r'▶️ 下一步：.*', '', response).strip()
                print(f"   ✅ 响应: {clean[:80]}")
            else:
                err = (result.stderr or "").strip() or "（无输出）"
                print(f"   ❌ {err[:100]}")
        except subprocess.TimeoutExpired:
            print(f"   ❌ 超时")
        except Exception as e:
            print(f"   ❌ 错误: {e}")

    print("\n" + "=" * 60)
    print("OpenCode 桥接测试完成")
    print("=" * 60)


def test_integration_check():
    """测试与 OpenCode 的集成"""
    print("\n" + "=" * 60)
    print("测试 OpenCode 集成")
    print("=" * 60)

    # 检查 opencode 是否可用
    try:
        result = subprocess.run(["which", "opencode"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ OpenCode 可用: {result.stdout.strip()}")
        else:
            print(f"  ❌ OpenCode 未安装")
    except Exception as e:
        print(f"  ❌ 检查失败: {e}")

    # 检查项目核心文件
    components = [
        ("feishu_integration.py", "飞书-OpenCode 桥接"),
    ]

    for file_name, component in components:
        file_path = BASE_DIR / "src" / file_name
        if file_path.exists():
            print(f"  ✅ {component} ({file_name})")
        else:
            print(f"  ❌ {component} ({file_name}) - 文件不存在")

    print("\n" + "=" * 60)
    print("集成检查完成")
    print("=" * 60)


def main():
    """主函数"""
    setup_logging()
    print("飞书/Lark 机器人集成测试套件")
    print("=" * 60)

    # 运行所有测试
    test_feishu_integration()
    test_message_handling()
    test_opencode_bridge()
    test_integration_check()

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
