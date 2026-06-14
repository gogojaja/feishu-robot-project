#!/bin/bash
# Free API Hub — 飞书机器人停止脚本
# 停止飞书/Lark 机器人服务

set -e

HUB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HUB_DIR"

echo "========================================"
echo "  飞书/Lark 机器人停止"
echo "========================================"
echo ""

# 查找并停止飞书机器人进程
if [ -f "feishu_bot.pid" ]; then
    BOT_PID=$(cat "feishu_bot.pid")
    if kill -0 $BOT_PID 2>/dev/null; then
        echo "正在停止飞书机器人 (PID: $BOT_PID)..."
        kill $BOT_PID
        sleep 2
        if kill -0 $BOT_PID 2>/dev/null; then
            echo "强制终止飞书机器人..."
            kill -9 $BOT_PID
        fi
        echo "✅ 飞书机器人已停止"
    else
        echo "⚠️  飞书机器人进程已不存在"
    fi
    rm -f "feishu_bot.pid"
else
    # 查找飞书机器人进程
    BOT_PID=$(pgrep -f "feishu_integration.py" | head -1)
    if [ -n "$BOT_PID" ]; then
        echo "正在停止飞书机器人 (PID: $BOT_PID)..."
        kill $BOT_PID
        sleep 2
        if kill -0 $BOT_PID 2>/dev/null; then
            echo "强制终止飞书机器人..."
            kill -9 $BOT_PID
        fi
        echo "✅ 飞书机器人已停止"
    else
        echo "⚠️  未找到飞书机器人进程"
    fi
fi

echo ""
echo "========================================"
echo "  🎉 飞书机器人停止完成！"
echo "========================================"
