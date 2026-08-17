#!/usr/bin/env bash
#
# 模块名称：pre-commit-env-gate.sh
# 功能描述：git pre-commit 环境门禁钩子——提交前校验 台账/25_环境资源清单.csv，
#           禁止出现「同端口被不同项目以 已占用 状态重复登记」的冲突，确保先注册先得不被破坏。
# 对外接口：
#     - pre-commit-env-gate.sh : 无参，供 .git/hooks/pre-commit 调用
# 依赖：
#     - 标准库：bash 内建
#     - 第三方：无
#     - 项目内：台账/25_环境资源清单.csv
# 版本：v1.0
# 更新记录：
#     - 2026-08-17: 环境治理 pre-commit 门禁初版
#
set -euo pipefail

LEDGER="台账/25_环境资源清单.csv"
DEBUG=${DEBUG:-0}
[ "$DEBUG" = "1" ] && set -x

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

echo "ENV-GATE: OK，无端口占用冲突"
exit 0
