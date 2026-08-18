#!/usr/bin/env python3
"""
模块名称：environment_check
功能描述：环境验证脚本，用于验证项目环境配置
对外接口：
    - check_env_type：检查环境类型标记
    - check_abandoned：检查废弃 webhook 链路残留（ADR-001）
    - check_openclaw_gateway：检查 OpenClaw 主链路
    - check_project_structure：检查项目结构
依赖：
    - 标准库：os, sys, json, logging, subprocess, tempfile, pathlib, datetime, urllib.parse
    - 第三方：requests, flask
版本：v1.1
更新记录：
    - 2026-06-15: 初始创建，提供环境验证功能
    - 2026-08-18: 移除 510x 端口检查，新增废弃 webhook 链路残留阻断（ADR-001）
"""

import os
import sys
from pathlib import Path

def check_env_type():
    """检查环境类型标记"""
    env_file = Path("/Volumes/KINGSTON120G/feishu-robot-project/.env_type")
    if not env_file.exists():
        print("❌ .env_type 文件不存在")
        return False
    
    content = env_file.read_text().strip()
    if content != "test":
        print(f"❌ .env_type 文件内容不正确: '{content}'，期望: 'test'")
        return False
    
    print(f"✅ .env_type 文件内容正确: '{content}'")
    return True

ABANDONED_MARKERS = [
    "src/feishu_integration.py",
    "scripts/start-feishu.sh",
    "scripts/stop-feishu.sh",
    "scripts/install-launchd.sh",
    "scripts/test_feishu.py",
    "scripts/benchmark_p95.py",
    "scripts/launchd/com.feishu.opencode-bridge.plist",
    "scripts/launchd/com.feishu.opencode-serve.plist",
    "config/feishu.yaml",
]

ABANDONED_PORTS = [5102, 5103]


def check_abandoned():
    """检查废弃 webhook 链路残留（ADR-001 已废弃：主链路为 OpenClaw 长连接）

    任一命中即阻断：废弃代码文件、5102/5103 端口、ngrok 进程。
    """
    import socket
    import subprocess

    ok = True
    root = Path("/Volumes/KINGSTON120G/feishu-robot-project")

    for rel in ABANDONED_MARKERS:
        if (root / rel).exists():
            print(f"❌ 废弃残留: {rel} 仍存在（ADR-001 已废弃 webhook 桥，请删除）")
            ok = False

    for port in ABANDONED_PORTS:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        if s.connect_ex(('127.0.0.1', port)) == 0:
            print(f"❌ 废弃残留: 端口 {port} 仍被监听（废弃链路未停）")
            ok = False
        s.close()

    try:
        out = subprocess.run(["pgrep", "-f", "ngrok"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            print("❌ 废弃残留: ngrok 进程仍在运行（ADR-001 已弃用）")
            ok = False
    except Exception:
        pass

    if ok:
        print("✅ 无废弃 webhook 链路残留（OpenClaw 长连接为唯一主链路）")
    return ok

def check_openclaw_gateway():
    """检查 OpenClaw Gateway 与 feishu 长连接（主链路，ADR-001）"""
    ok = True
    try:
        if os.system("command -v openclaw >/dev/null 2>&1") == 0:
            print("✅ openclaw CLI 已安装")
        else:
            print("❌ openclaw 未安装（主链路缺失）")
            return False
    except Exception as e:
        print(f"❌ openclaw 检查异常: {e}")
        return False

    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    if s.connect_ex(('127.0.0.1', 18789)) == 0:
        print("✅ OpenClaw Gateway 18789 监听正常")
    else:
        print("❌ OpenClaw Gateway 18789 未监听（主链路中断）")
        ok = False
    s.close()

    try:
        out = os.popen("openclaw channels status 2>&1").read()
        if "Feishu default" in out and "not-running" not in out.split("Feishu default")[1][:200]:
            print("✅ feishu 长连接渠道 running")
        else:
            print("⚠️ feishu 渠道状态异常（可能 crash-loop breaker 抑制或 secret 问题）")
            for line in out.splitlines():
                if "Feishu" in line:
                    print(f"    {line.strip()}")
            ok = False
    except Exception as e:
        print(f"❌ feishu 渠道检查异常: {e}")
        ok = False
    return ok


def check_project_structure():
    """检查项目结构"""
    required_files = [
        "README.md",
        "requirements.txt",
        "scripts/check_env.py",
        "scripts/openclaw-gate-check.sh",
        "scripts/pre-commit-env-gate.sh"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 文件不存在")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("环境验证脚本")
    print("=" * 60)
    
    checks = [
        ("环境类型验证", check_env_type),
        ("废弃链路残留检查", check_abandoned),
        ("OpenClaw 主链路检查", check_openclaw_gateway),
        ("项目结构检查", check_project_structure)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有环境检查通过")
    else:
        print("❌ 环境检查失败，请修复问题后重试")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())