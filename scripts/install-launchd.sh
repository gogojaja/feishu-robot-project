#!/bin/bash
# 安装/卸载 launchd 进程守护（飞书桥接 + opencode serve）
# 用法: bash scripts/install-launchd.sh [install|uninstall|status]
set -e
PROJ="/Volumes/KINGSTON120G/feishu-robot-project"
LA="$HOME/Library/LaunchAgents"
LABELS=("com.feishu.opencode-bridge" "com.feishu.opencode-serve")

install() {
    echo "== 安装 launchd 守护 =="
    mkdir -p "$LA"
    # 先停止现有 nohup 服务避免端口冲突
    bash "$PROJ/scripts/stop-feishu.sh" || true
    for label in "${LABELS[@]}"; do
        cp "$PROJ/scripts/launchd/$label.plist" "$LA/"
        launchctl unload "$LA/$label.plist" 2>/dev/null || true
        launchctl load "$LA/$label.plist"
        echo "  ✅ $label 已加载"
    done
    sleep 3
    echo "  健康检查:"
    curl -s -o /dev/null -w "  /health -> %{http_code}\n" http://127.0.0.1:5103/health || echo "  ⚠️ 健康检查失败"
}

uninstall() {
    echo "== 卸载 launchd 守护 =="
    for label in "${LABELS[@]}"; do
        launchctl unload "$LA/$label.plist" 2>/dev/null || true
        rm -f "$LA/$label.plist"
        echo "  ✅ $label 已卸载"
    done
}

status() {
    echo "== launchd 状态 =="
    for label in "${LABELS[@]}"; do
        if launchctl list | grep -q "$label"; then
            echo "  ✅ $label 运行中"
        else
            echo "  ⚠️ $label 未运行"
        fi
    done
    curl -s http://127.0.0.1:5103/health && echo
}

case "${1:-install}" in
    install) install ;;
    uninstall) uninstall ;;
    status) status ;;
    *) echo "用法: $0 [install|uninstall|status]"; exit 1 ;;
esac
