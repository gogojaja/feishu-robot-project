#!/bin/bash
set -e
HUB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HUB_DIR"

if [ -f feishu_bot.pid ]; then
    PID=$(cat feishu_bot.pid)
    kill $PID 2>/dev/null && echo "✅ 已停止 (PID: $PID)" || echo "⚠️ 进程不存在"
    rm -f feishu_bot.pid
else
    PID=$(pgrep -f "feishu_integration.py" | head -1)
    if [ -n "$PID" ]; then
        kill $PID 2>/dev/null
        echo "✅ 已停止 (PID: $PID)"
    else
        echo "⚠️ 未找到运行中的服务"
    fi
fi

# 终止 opencode serve 常驻服务
if [ -f opencode_server.pid ]; then
    SID=$(cat opencode_server.pid)
    kill $SID 2>/dev/null && echo "✅ opencode serve 已停止 (PID: $SID)" || echo "⚠️ serve 进程不存在"
    rm -f opencode_server.pid
else
    SPID=$(pgrep -f "opencode serve --port 5102" | head -1)
    if [ -n "$SPID" ]; then
        kill $SPID 2>/dev/null
        echo "✅ opencode serve 已停止 (PID: $SPID)"
    fi
fi