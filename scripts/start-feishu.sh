#!/bin/bash
# Free API Hub — 飞书机器人启动脚本
# 启动飞书/Lark 机器人服务，实现移动端编程交互

set -e

HUB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HUB_DIR"

echo "========================================"
echo "  飞书/Lark 机器人启动"
echo "========================================"
echo ""

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✅ Python3 可用"

# 检查必要的文件
if [ ! -f "src/feishu_integration.py" ]; then
    echo "❌ feishu_integration.py 不存在"
    exit 1
fi

echo "✅ feishu_integration.py 存在"

# 设置环境变量
export PYTHONPATH="$HUB_DIR/src:$PYTHONPATH"

# 启动飞书机器人
echo "正在启动飞书机器人..."
python3 src/feishu_integration.py &

BOT_PID=$!
echo "飞书机器人已启动，PID: $BOT_PID"

echo ""
echo "========================================"
echo "  🎉 飞书机器人启动完成！"
echo "========================================"
echo ""
echo "服务信息:"
echo "  端口: 5103"
echo "  路径: $HUB_DIR/src/feishu_integration.py"
echo "  PID: $BOT_PID"
echo ""
echo "检查状态:"
echo "  curl http://127.0.0.1:5103/health"
echo ""
echo "停止服务:"
echo "  kill $BOT_PID"
echo ""
echo "========================================"
