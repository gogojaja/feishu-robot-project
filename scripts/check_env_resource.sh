#!/usr/bin/env bash
#
# 模块名称：check_env_resource.sh
# 功能描述：环境资源申请门禁——校验任一独占资源（端口/容器/模型/目录/数据库等）是否已在
#           台账/25_环境资源清单.csv 注册，冲突即阻断（先注册先得 + 冲突仲裁留痕）。
# 对外接口：
#     - check_env_resource.sh <type> <identifier> [project] : 校验资源占用与归属
#       例: check_env_resource.sh 端口 5103 feishu-robot-project
#           check_env_resource.sh 容器 mysql-01
#           check_env_resource.sh 模型 llama3-8b
# 依赖：
#     - 标准库：bash 内建
#     - 第三方：无
#     - 项目内：台账/25_环境资源清单.csv
# 版本：v1.1
# 更新记录：
#     - 2026-08-17: 环境治理门禁初版（仅端口）
#     - 2026-08-17: 扩展至全资源类型（端口/容器/模型/目录等），按 资源类型+资源标识 通用匹配
#
set -euo pipefail

LEDGER="台账/25_环境资源清单.csv"
DEBUG=${DEBUG:-0}
[ "$DEBUG" = "1" ] && set -x

if [ ! -f "$LEDGER" ]; then
  echo "ERROR: 未找到治理台账 $LEDGER" >&2
  exit 2
fi

TYPE="${1:-}"
IDENT="${2:-}"
PROJECT="${3:-}"

if [ -z "$TYPE" ] || [ -z "$IDENT" ]; then
  echo "用法: $0 <type> <identifier> [project]" >&2
  echo "  type: 端口|容器|模型|目录|数据库|缓存|GPU|域名|Docker运行时" >&2
  exit 2
fi

# 跳过表头，匹配 资源类型(col2)==TYPE 且 资源标识(col3)==IDENT
MATCH=$(awk -F',' "NR>1 && \$2==\"$TYPE\" && \$3==\"$IDENT\" {print}" "$LEDGER")

if [ -z "$MATCH" ]; then
  echo "OK: 资源 [$TYPE:$IDENT] 未在台账注册，可先注册后使用"
  exit 0
fi

STATUS=$(echo "$MATCH" | awk -F',' '{print $10}')
OWNER=$(echo "$MATCH" | awk -F',' '{print $8}')

if [ "$STATUS" = "已占用" ]; then
  if [ -n "$PROJECT" ] && [ "$OWNER" != "$PROJECT" ]; then
    echo "BLOCK: 资源 [$TYPE:$IDENT] 已被 $OWNER 占用(状态=$STATUS)，与申请方 $PROJECT 冲突，禁止抢占"
    exit 1
  fi
  echo "OK: 资源 [$TYPE:$IDENT] 已由 $OWNER 占用(状态=$STATUS)，归属一致"
  exit 0
fi

echo "WARN: 资源 [$TYPE:$IDENT] 状态=$STATUS (占用方=$OWNER)，请确认后再注册"
exit 0
