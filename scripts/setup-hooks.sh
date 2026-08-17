#!/usr/bin/env bash
#
# 模块名称：setup-hooks.sh
# 功能描述：一键安装本仓库 git hooks（环境门禁 pre-commit），解决钩子不随 clone 分发的问题。
#           克隆仓库后运行一次即可启用提交级环境冲突阻断。
# 对外接口：
#     - setup-hooks.sh : 无参，将 scripts/pre-commit-env-gate.sh 安装为 .git/hooks/pre-commit
# 依赖：
#     - 标准库：bash 内建
#     - 第三方：无
#     - 项目内：scripts/pre-commit-env-gate.sh
# 版本：v1.0
# 更新记录：
#     - 2026-08-17: 环境门禁钩子分发安装初版
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/pre-commit-env-gate.sh"
HOOK_DIR="$ROOT/.git/hooks"
DST="$HOOK_DIR/pre-commit"

DEBUG=${DEBUG:-0}
[ "$DEBUG" = "1" ] && set -x

if [ ! -f "$SRC" ]; then
  echo "ERROR: 未找到钩子源文件 $SRC" >&2
  exit 2
fi

mkdir -p "$HOOK_DIR"
cp "$SRC" "$DST"
chmod +x "$DST"
echo "OK: 已安装 pre-commit 环境门禁钩子 -> $DST"
echo "    验证: 修改 台账/25_环境资源清单.csv 制造端口冲突后提交，将被 ENV-GATE 阻断"
exit 0
