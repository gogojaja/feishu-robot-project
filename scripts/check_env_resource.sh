#!/usr/bin/env bash
#
# 模块名称：check_env_resource.sh
# 功能描述：环境资源申请门禁——校验端口/目录是否已在 台账/25_环境资源清单.csv 注册，
#           冲突即阻断（先注册先得 + 冲突仲裁留痕）。
# 对外接口：
#     - check_env_resource.sh <port> [project] : 校验端口占用与归属
# 依赖：
#     - 标准库：bash 内建
#     - 第三方：无
#     - 项目内：台账/25_环境资源清单.csv
# 版本：v1.0
# 更新记录：
#     - 2026-08-17: 环境治理门禁初版
#
set -euo pipefail

LEDGER="台账/25_环境资源清单.csv"
DEBUG=${DEBUG:-0}
[ "$DEBUG" = "1" ] && set -x

if [ ! -f "$LEDGER" ]; then
  echo "ERROR: 未找到治理台账 $LEDGER" >&2
  exit 2
fi

PORT="${1:-}"
PROJECT="${2:-}"

if [ -z "$PORT" ]; then
  echo "用法: $0 <port> [project]" >&2
  exit 2
fi

# 跳过表头，匹配 端口 行且该端口值等于 PORT
MATCH=$(awk -F',' "NR>1 && \$2==\"端口\" && \$5==\"$PORT\" {print}" "$LEDGER")

if [ -z "$MATCH" ]; then
  echo "OK: 端口 $PORT 未在台账注册，可先注册后使用"
  exit 0
fi

STATUS=$(echo "$MATCH" | awk -F',' '{print $10}')
OWNER=$(echo "$MATCH" | awk -F',' '{print $8}')

if [ "$STATUS" = "已占用" ]; then
  if [ -n "$PROJECT" ] && [ "$OWNER" != "$PROJECT" ]; then
    echo "BLOCK: 端口 $PORT 已被 $OWNER 占用(状态=$STATUS)，与申请方 $PROJECT 冲突，禁止抢占"
    exit 1
  fi
  echo "OK: 端口 $PORT 已由 $OWNER 占用(状态=$STATUS)，归属一致"
  exit 0
fi

echo "WARN: 端口 $PORT 状态=$STATUS (占用方=$OWNER)，请确认后再注册"
exit 0
