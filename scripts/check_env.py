#!/usr/bin/env python3
"""
模块名称：environment_check
功能描述：环境验证脚本，用于验证项目环境配置
对外接口：
    - check_env_type：检查环境类型标记
    - check_port_usage：检查端口使用情况
    - check_project_structure：检查项目结构
依赖：
    - 标准库：os, sys, json, logging, subprocess, tempfile, pathlib, datetime, urllib.parse
    - 第三方：requests, flask
版本：v1.0
更新记录：
    - 2026-06-15: 初始创建，提供环境验证功能
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

def check_port_usage():
    """检查端口使用情况"""
    try:
        import socket
        test_ports = [5101, 5102, 5103]
        for port in test_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                print(f"⚠️  端口 {port} 已被占用")
            else:
                print(f"✅ 端口 {port} 可用")
    except Exception as e:
        print(f"❌ 端口检查失败: {e}")
        return False
    return True

def check_project_structure():
    """检查项目结构"""
    required_files = [
        "src/feishu_integration.py",
        "README.md",
        "requirements.txt",
        "config/feishu.yaml",
        "scripts/start-feishu.sh",
        "scripts/stop-feishu.sh",
        "scripts/test_feishu.py"
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
        ("端口使用检查", check_port_usage),
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