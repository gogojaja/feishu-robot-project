#!/usr/bin/env bash
#
# 模块名称：pre-commit-env-gate.sh
# 功能描述：git pre-commit 环境门禁钩子——
#           ① 校验 台账/25_环境资源清单.csv 无「同端口被不同项目以 已占用 状态重复登记」冲突；
#           ② 阻断废弃 webhook 桥（ADR-001）代码/引用 reintroduce（防止 5102/5103/ngrok 复活）。
# 对外接口：
#     - pre-commit-env-gate.sh : 无参，供 .git/hooks/pre-commit 调用
# 依赖：
#     - 标准库：bash 内建
#     - 第三方：无
#     - 项目内：台账/25_环境资源清单.csv
# 版本：v1.1
# 更新记录：
#     - 2026-08-17: 环境治理 pre-commit 门禁初版
#     - 2026-08-18: 新增废弃 webhook 桥残留阻断（ADR-001 彻底废弃闭环）
#
set -euo pipefail

LEDGER="台账/25_环境资源清单.csv"
DEBUG=${DEBUG:-0}
[ "$DEBUG" = "1" ] && set -x

# 废弃 webhook 桥标记文件（ADR-001 已废弃，禁止 reintroduce）
ABANDONED_PATTERNS=(
  "src/feishu_integration.py"
  "scripts/start-feishu.sh"
  "scripts/stop-feishu.sh"
  "scripts/install-launchd.sh"
  "scripts/test_feishu.py"
  "scripts/benchmark_p95.py"
  "scripts/launchd/com.feishu.opencode-bridge.plist"
  "scripts/launchd/com.feishu.opencode-serve.plist"
  "config/feishu.yaml"
)

# ① 废弃残留阻断：暂存文件中出现废弃标记即阻断（精确行匹配）
STAGED=$(git diff --cached --name-only --diff-filter=ACM || true)
for pat in "${ABANDONED_PATTERNS[@]}"; do
  if printf '%s\n' "$STAGED" | grep -Fxq "$pat"; then
    echo "ENV-GATE BLOCK: 废弃文件 $pat 被 reintroduce（ADR-001 已废弃 webhook 桥）"
    exit 1
  fi
done

# ② 端口台账冲突检查

if [ ! -f "$LEDGER" ]; then
  echo "ENV-GATE: 跳过（未找到 $LEDGER）"
  exit 0
fi

# 用 awk 提取 端口/已占用 行的 端口(col5)->项目(col8)，检测同端口多项目冲突
if ! CONFLICTS=$(awk -F',' '
  NR>1 && $2=="端口" && $10=="已占用" {
    port=$5; owner=$8
    if (seen[port]!="" && seen[port]!=owner) {
      print "ENV-GATE BLOCK: 端口 "port" 被多项目以 已占用 重复登记 -> "seen[port]" 与 "owner
      bad=1
    } else {
      seen[port]=owner
    }
  }
  END { exit (bad==1?1:0) }
' "$LEDGER"); then
  echo "$CONFLICTS"
  echo "ENV-GATE: 提交被阻断——请先消解上述端口冲突（更新 25_环境资源清单.csv）"
  exit 1
fi

echo "ENV-GATE: OK，无端口占用冲突且无废弃桥残留"
exit 0
