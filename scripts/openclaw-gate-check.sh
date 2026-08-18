#!/bin/bash
# =========================================================
# OpenClaw Gateway 配置变更门禁
# 功能：备份配置 → 校验 JSON → 重启 Gateway → 验证 feishu 渠道
# 用法：修改 ~/.openclaw/openclaw.json 后运行本脚本
# =========================================================
set -e
CFG="$HOME/.openclaw/openclaw.json"
TS=$(date +%Y%m%d%H%M%S)

echo "========================================"
echo "OpenClaw Gateway 配置变更门禁"
echo "========================================"

# 1. 配置存在性
[ -f "$CFG" ] || { echo "❌ 配置不存在: $CFG"; exit 1; }
echo "✅ 配置存在: $CFG"

# 2. 备份
cp "$CFG" "$CFG.bak-$TS"
echo "✅ 已备份: $CFG.bak-$TS"

# 3. JSON 语法校验
python3 -c "import json; json.load(open('$CFG')); print('✅ JSON 语法有效')"

# 4. appSecret 关键校验（禁止 env 未配置引用）
python3 - "$CFG" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
fs = (cfg.get("channels") or {}).get("feishu") or {}
acc = (fs.get("accounts") or {}).get("default") or {}
sec = acc.get("appSecret")
if isinstance(sec, dict) and sec.get("source") == "env":
    # env 引用需确认 secrets.providers.env 已配置
    prov = (cfg.get("secrets") or {}).get("providers") or {}
    if not prov.get("env"):
        print("❌ appSecret 为 env 引用但 secrets.providers.env 未配置，将导致 Gateway 无法启动")
        print("   修复：改为明文 appSecret 或先配置 env provider")
        sys.exit(1)
print("✅ appSecret 配置合法")
PY

# 5. Gateway 服务状态确认
command -v openclaw >/dev/null || { echo "❌ openclaw 未安装"; exit 1; }
openclaw gateway status >/dev/null 2>&1 && echo "✅ openclaw CLI 可用" || echo "⚠️ Gateway 未运行（执行 restart）"

# 6. 重启 Gateway
echo "--- 重启 Gateway ---"
openclaw gateway restart

# 7. 等待就绪并验证 feishu 渠道
echo "--- 等待 Gateway 就绪 ---"
for i in $(seq 1 15); do
    sleep 2
    if lsof -ti:18789 >/dev/null 2>&1; then
        echo "✅ Gateway 已监听 18789 (${i}x2s)"
        break
    fi
done
sleep 4
STATUS=$(openclaw channels status 2>&1 | grep -i "Feishu")
echo "$STATUS"
if echo "$STATUS" | grep -q "running"; then
    echo "✅ Feishu 长连接已建立"
    echo "   参考: openclaw logs --follow 观察 feishu ws connected"
    exit 0
else
    echo "⚠️ Feishu 未 running —— 可能存在 crash-loop breaker 抑制或 secret 问题"
    echo "   排查: openclaw gw stability; openclaw logs | grep -i secret"
    echo "   若 breaker: 等待 5 分钟窗口衰减，或确保 Gateway 连续稳定启动"
    echo "   最终期望: channels status 中 Feishu=running 且日志出现 feishu ws connected"
    exit 1
fi