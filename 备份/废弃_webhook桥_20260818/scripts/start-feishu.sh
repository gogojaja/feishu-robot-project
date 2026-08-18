#!/bin/bash
set -e
HUB_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo "  飞书 → OpenCode 桥接服务"
echo "========================================"
echo ""

command -v python3 &>/dev/null || { echo "❌ Python3 未安装"; exit 1; }
echo "✅ Python3"

command -v opencode &>/dev/null || { echo "❌ opencode 未安装"; exit 1; }
echo "✅ opencode $(opencode --version)"

# 清除认证环境变量，避免 opencode run 报 Session not found
export OPENCODE_SERVER_PASSWORD=""
export OPENCODE_SERVER_USERNAME=""

cd "$HUB_DIR"

# 停止旧进程（飞书服务 + opencode serve）
pgrep -f "feishu_integration.py" | head -1 | xargs -r kill 2>/dev/null || true
pkill -f "opencode serve --port 5102" 2>/dev/null || true
sleep 1

# 启动 opencode serve 常驻服务（独立 DB，避免全局库 schema 问题）
mkdir -p "$HUB_DIR/var"
nohup env OPENCODE_DB="$HUB_DIR/var/opencode.db" opencode serve --port 5102 --hostname 127.0.0.1 > "$HUB_DIR/opencode_server.log" 2>&1 &
SERVE_PID=$!
echo $SERVE_PID > "$HUB_DIR/opencode_server.pid"
# 等待 serve 就绪（最长 15s）
for i in $(seq 1 15); do
    if curl -s -o /dev/null -m 2 http://127.0.0.1:5102 >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
echo "✅ opencode serve (PID: $SERVE_PID) 端口: 5102"

nohup python3 src/feishu_integration.py > feishu_bot.log 2>&1 &
PID=$!
echo $PID > feishu_bot.pid
sleep 2

PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('$HUB_DIR/config/feishu.yaml')).get('port', 5103))" 2>/dev/null || echo 5101)
if kill -0 $PID 2>/dev/null; then
    echo "✅ 服务已启动 (PID: $PID)"
    echo "   端口: $PORT  日志: feishu_bot.log"
    echo "   健康检查: curl http://127.0.0.1:$PORT/health"
else
    echo "❌ 启动失败"
    cat feishu_bot.log
    exit 1
fi
echo "========================================"