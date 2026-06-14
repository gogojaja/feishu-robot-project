"""
模块名称：feishu_test
功能描述：Feishu/Lark 机器人集成测试脚本
对外接口：
    - test_feishu_integration：测试飞书集成功能
    - test_message_handling：测试消息处理
    - test_code_execution：测试代码执行
依赖：
    - 标准库：os, sys, json, logging, subprocess, tempfile, pathlib, datetime, urllib.parse
    - 第三方：requests, flask
    - 项目内：shared.feishu_api, assistants.chat-assistant.src.main (talk, search), assistants.office-assistant.src.core (WordProcessor, ExcelProcessor, DocumentSummarizer), assistants.life-assistant.src.scheduler, assistants.file-assistant.src.file_manager, assistants.sys-assistant.src.system_monitor
版本：v1.0
更新记录：
    - 2026-06-14: 初始创建，提供测试用例
    - 2026-06-15: 更新测试脚本，匹配简化架构
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


def test_code_execution():
    """测试代码执行"""
    print("\n" + "=" * 60)
    print("测试代码执行")
    print("=" * 60)

    test_codes = [
        "print('Hello, World!')",
        "def add(a, b):\n    return a + b\nprint(add(1, 2))",
        "import json\ndata = {'name': 'test', 'value': 123}\nprint(json.dumps(data))"
    ]

    for i, code in enumerate(test_codes, 1):
        print(f"\n{i}. 执行代码:")
        print(f"   代码: {code[:50]}...")

        # 创建临时文件执行代码
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # 执行代码
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(BASE_DIR)
            )

            print(f"   执行结果:")
            if result.stdout:
                print(f"     输出: {result.stdout.strip()}")
            if result.stderr:
                print(f"     错误: {result.stderr.strip()}")
            print(f"     退出码: {result.returncode}")

        except subprocess.TimeoutExpired:
            print(f"   执行超时")
        except Exception as e:
            print(f"   执行失败: {e}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    print("\n" + "=" * 60)
    print("代码执行测试完成")
    print("=" * 60)


def test_integration_with_free_api_hub():
    """测试与 Free API Hub 的集成"""
    print("\n" + "=" * 60)
    print("测试与 Free API Hub 的集成")
    print("=" * 60)

    # 检查 Free API Hub 组件
    components = [
        ("agent.py", "AI Agent 层"),
        ("gateway.py", "APIGateway"),
        ("server.py", "Flask 服务"),
        ("feishu_integration.py", "飞书集成")
    ]

    for file_name, component in components:
        file_path = BASE_DIR / "src" / file_name
        if file_path.exists():
            print(f"  ✅ {component} ({file_name})")
        else:
            print(f"  ❌ {component} ({file_name}) - 文件不存在")

    # 检查脚本
    scripts = [
        "scripts/start.sh",
        "scripts/stop.sh",
        "scripts/start-feishu.sh",
        "scripts/stop-feishu.sh"
    ]

    print("\n  脚本:")
    for script in scripts:
        script_path = BASE_DIR / script
        if script_path.exists():
            print(f"    ✅ {script}")
        else:
            print(f"    ❌ {script}")

    print("\n" + "=" * 60)
    print("集成测试完成")
    print("=" * 60)


def main():
    """主函数"""
    setup_logging()
    print("飞书/Lark 机器人集成测试套件")
    print("=" * 60)

    # 运行所有测试
    test_feishu_integration()
    test_message_handling()
    test_code_execution()
    test_integration_with_free_api_hub()

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
