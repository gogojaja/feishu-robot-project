"""
模块名称：diag_cardkit_400.py
功能描述：飞书流式卡片 HTTP 400（99991672）诊断脚本，复现错误 + 查询权限授权状态 + 查询应用版本
对外接口：
    - main(): 执行完整诊断流程
依赖：
    - 标准库：json, os, sys, urllib.request, urllib.error, urllib.parse, pathlib
    - 第三方：无（纯标准库，任意 Python3 可跑）
    - 项目内：读取 ~/.openclaw/openclaw.json 凭据
版本：v1.0
更新记录：
    - 2026-08-19: 初始版本，基于排查交接_流式卡片400_20260819.md §3.2 复现脚本扩展
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# ===== 配置 =====
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
DEBUG = True  # 内置 DEBUG 级日志开关


def log(msg, level="INFO"):
    if DEBUG or level in ("ERROR", "WARN", "RESULT"):
        print(f"[{level}] {msg}")


def load_credentials():
    """从 ~/.openclaw/openclaw.json 读取飞书 appId/appSecret"""
    log(f"读取配置: {OPENCLAW_CONFIG}")
    if not OPENCLAW_CONFIG.exists():
        log(f"配置文件不存在: {OPENCLAW_CONFIG}", "ERROR")
        sys.exit(1)
    with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    account = cfg.get("channels", {}).get("feishu", {}).get("accounts", {}).get("default", {})
    app_id = account.get("appId")
    app_secret = account.get("appSecret")
    if not app_id or not app_secret:
        log("未找到 appId/appSecret，请检查 openclaw.json", "ERROR")
        sys.exit(1)
    log(f"应用 appId: {app_id}")
    return app_id, app_secret


def get_tenant_token(app_id, app_secret):
    """获取 tenant_access_token"""
    url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
    body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log(f"获取 token HTTP 错误: {e.code} {e.reason}", "ERROR")
        sys.exit(1)
    except Exception as e:
        log(f"获取 token 异常: {e}", "ERROR")
        sys.exit(1)
    if data.get("code") != 0:
        log(f"获取 token 失败: code={data.get('code')} msg={data.get('msg')}", "ERROR")
        sys.exit(1)
    token = data.get("tenant_access_token")
    log(f"token 获取成功 (前12位: {token[:12]}...)")
    return token


def reproduce_cardkit_400(token):
    """复现 cardkit/v1/cards 调用，展示 400 错误详情"""
    log("=" * 60)
    log("【步骤1】复现 cardkit/v1/cards 流式卡片创建请求")
    url = f"{FEISHU_API_BASE}/cardkit/v1/cards"

    # 构造最小流式卡片 JSON（schema 2.0 + streaming_mode true）
    card_json = {
        "schema": "2.0",
        "config": {"streaming_mode": True},
        "body": {"elements": [{"tag": "markdown", "content": "诊断测试卡片"}]},
    }
    # openclaw 源码请求体格式：{type:"card_json", data: JSON.stringify(cardJson)}
    body = json.dumps({
        "type": "card_json",
        "data": json.dumps(card_json, ensure_ascii=False),
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json; charset=utf-8")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            log(f"HTTP {resp.status} (预期 400，实际成功？)", "WARN")
            log(f"返回: {json.dumps(data, ensure_ascii=False, indent=2)}", "RESULT")
            return data
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        try:
            err = json.loads(body_text)
        except Exception:
            err = body_text
        log(f"HTTP {e.code} {e.reason}", "RESULT")
        log(f"返回体: {json.dumps(err, ensure_ascii=False, indent=2)}", "RESULT")
        # 提取关键信息
        if isinstance(err, dict):
            code = err.get("code")
            msg = err.get("msg")
            violations = err.get("error", {}).get("permission_violations", [])
            log(f"错误码: {code} | 消息: {msg}", "RESULT")
            if violations:
                for v in violations:
                    log(f"权限缺失: type={v.get('type')} subject={v.get('subject')}", "RESULT")
        return err
    except Exception as e:
        log(f"请求异常: {e}", "ERROR")
        return None


def query_scopes(token, app_id):
    """查询租户授权的应用权限状态 (application/v6/scopes)"""
    log("=" * 60)
    log("【步骤2】查询租户授权状态 (application/v6/scopes)")
    url = f"{FEISHU_API_BASE}/application/v6/scopes?app_id={app_id}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        log(f"HTTP {e.code} {e.reason}", "ERROR")
        log(f"返回: {body_text[:500]}", "ERROR")
        return None
    except Exception as e:
        log(f"请求异常: {e}", "ERROR")
        return None

    if data.get("code") != 0:
        log(f"查询失败: code={data.get('code')} msg={data.get('msg')}", "ERROR")
        return data

    scopes = data.get("data", {}).get("scopes", [])
    log(f"已授权权限数: {len(scopes)}", "RESULT")
    cardkit_found = False
    cardkit_scope_types = []
    for s in scopes:
        scope_name = s.get("scope_name", "")
        grant = s.get("grant_status")
        scope_type = s.get("scope_type", "")
        flag = " <== cardkit:card:write" if scope_name == "cardkit:card:write" else ""
        log(f"  - {scope_name:50s} grant={grant} type={scope_type}{flag}", "RESULT")
        if scope_name == "cardkit:card:write":
            cardkit_found = True
            cardkit_scope_types.append(scope_type)
    if not cardkit_found:
        log("⚠️ cardkit:card:write 未出现在已授权列表中", "WARN")
    elif "tenant" not in cardkit_scope_types:
        log(f"⚠️ cardkit:card:write 仅授权为 {cardkit_scope_types} 身份，缺 tenant", "WARN")
        log("→ OpenClaw 使用 tenant_access_token（应用身份）调用，需 tenant 身份授权", "WARN")
    else:
        log(f"✅ cardkit:card:write 已授权，scope_type={cardkit_scope_types}", "RESULT")
    return data


def query_app_versions(token, app_id):
    """尝试查询应用版本列表（可能需要管理员权限，失败仅记录）"""
    log("=" * 60)
    log("【步骤3】尝试查询应用版本列表 (application/v6/applications/{app_id}/versions)")
    url = f"{FEISHU_API_BASE}/application/v6/applications/{app_id}/versions?lang=zh_cn&page_size=20"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            log(f"HTTP {resp.status}", "RESULT")
            versions = data.get("data", {}).get("items", [])
            log(f"版本数: {len(versions)}", "RESULT")
            for v in versions:
                vid = v.get("version_id")
                status = v.get("status")
                created = v.get("create_time")
                log(f"  - version_id={vid} status={status} created={created}", "RESULT")
            return data
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        log(f"HTTP {e.code} {e.reason}（此接口可能需平台管理员权限，失败可忽略）", "WARN")
        try:
            err = json.loads(body_text)
            log(f"返回: code={err.get('code')} msg={err.get('msg')}", "WARN")
        except Exception:
            log(f"返回: {body_text[:300]}", "WARN")
        return None
    except Exception as e:
        log(f"请求异常: {e}（此接口可能不可用，失败可忽略）", "WARN")
        return None


def query_app_info(token, app_id):
    """尝试查询应用信息（辅助判断应用能力状态）"""
    log("=" * 60)
    log("【步骤4】尝试查询应用信息 (application/v6/applications/{app_id})")
    url = f"{FEISHU_API_BASE}/application/v6/applications/{app_id}?lang=zh_cn"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            log(f"HTTP {resp.status}", "RESULT")
            app = data.get("data", {}).get("app", {})
            log(f"应用名: {app.get('app_name')} 状态: {app.get('status')}", "RESULT")
            return data
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8")
        log(f"HTTP {e.code} {e.reason}（此接口可能需平台管理员权限，失败可忽略）", "WARN")
        try:
            err = json.loads(body_text)
            log(f"返回: code={err.get('code')} msg={err.get('msg')}", "WARN")
        except Exception:
            log(f"返回: {body_text[:300]}", "WARN")
        return None
    except Exception as e:
        log(f"请求异常: {e}（此接口可能不可用，失败可忽略）", "WARN")
        return None


def diagnose(cardkit_result, scopes_result):
    """综合诊断结论"""
    log("=" * 60)
    log("【诊断结论】")
    cardkit_is_400 = False
    if isinstance(cardkit_result, dict):
        if cardkit_result.get("code") == 99991672 or "99991672" in json.dumps(cardkit_result):
            cardkit_is_400 = True

    scopes_has_cardkit = False
    cardkit_scope_type = None
    if isinstance(scopes_result, dict):
        scopes = scopes_result.get("data", {}).get("scopes", [])
        for s in scopes:
            if s.get("scope_name") == "cardkit:card:write" and s.get("grant_status") == 1:
                scopes_has_cardkit = True
                cardkit_scope_type = s.get("scope_type")

    if not cardkit_is_400:
        log("✅ cardkit 调用已恢复（非 400），问题已解决", "RESULT")
    elif cardkit_is_400 and scopes_has_cardkit and cardkit_scope_type == "user":
        log("✅ 根因确认：cardkit:card:write 仅授权为 user 身份，未授权 tenant 身份", "RESULT")
        log("→ OpenClaw 使用 tenant_access_token（应用身份）调用 cardkit API", "RESULT")
        log("→ 错误信息「应用尚未开通所需的应用身份权限」即指 scope_type=user 非 tenant", "RESULT")
        log("→ 处置：飞书开放平台 → 权限管理 → cardkit:card:write 开通「应用身份」权限", "RESULT")
        log("         路径：https://open.feishu.cn/app/cli_aa82c1b457b89bc3/auth?q=cardkit:card:write", "RESULT")
        log("         开通后可能需创建新版本发布生效，完成后重跑本脚本验证", "RESULT")
    elif cardkit_is_400 and scopes_has_cardkit:
        log("⚠️ scopes 显示已授权（type={}），但运行时报 99991672".format(cardkit_scope_type), "RESULT")
        log("→ 疑运行时权限基于已生效版本快照，需平台侧补发含该权限的新版本", "RESULT")
    elif cardkit_is_400 and not scopes_has_cardkit:
        log("⚠️ scopes 也未授权 cardkit:card:write", "RESULT")
        log("→ 处置：飞书开放平台 → 权限管理 → 开通 cardkit:card:write → 发布版本", "RESULT")
    else:
        log("诊断不明确，请人工分析上述输出", "WARN")


def main():
    log("=" * 60)
    log("飞书流式卡片 HTTP 400 诊断脚本 v1.0")
    log("=" * 60)

    app_id, app_secret = load_credentials()
    token = get_tenant_token(app_id, app_secret)

    cardkit_result = reproduce_cardkit_400(token)
    scopes_result = query_scopes(token, app_id)
    query_app_versions(token, app_id)
    query_app_info(token, app_id)

    diagnose(cardkit_result, scopes_result)
    log("=" * 60)
    log("诊断完成。")


if __name__ == "__main__":
    main()
