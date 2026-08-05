"""
模块名称：feishu_integration
功能描述：Feishu/Lark → OpenCode 桥接服务
对外接口：
    - FeishuBot：飞书机器人主类
    - main：启动入口
依赖：
    - 标准库：os, sys, json, logging, subprocess, re, pathlib, threading, time
    - 第三方：requests, flask
版本：v1.2
更新记录：
    - 2026-06-14: 初始创建
    - 2026-06-15: 重构为 OpenCode 桥接模式，加入会话追踪
    - 2026-06-15: dedup + 异步处理修复重复回复
    - 2026-08-05: C12 改造——发送失败重试 1 次 + token 连续失败≥3 告警（REQ-FUNC-REQ-017/018）
    - 2026-08-05: C10 限流 + C11 入站校验——固定窗口 10 条/分 + 4096 字符拒绝（REQ-SEC-REQ-003 / REQ-FUNC-REQ-012）
"""

import os
import sys
import re
import json
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict
import uuid
import requests
from flask import Flask, request, jsonify, make_response

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger("FeishuBot")


class FeishuBot:

    def __init__(self, app_id: str, app_secret: str, verification_token: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.tenant_access_token = ""
        self.token_expire_time = 0
        self._token_fail_count = 0
        self.sessions: Dict[str, str] = {}
        self._processed_ids: set = set()
        self._dedup_lock = threading.Lock()
        self._rate_limits: Dict[str, list] = {}
        self._rate_lock = threading.Lock()
        self.rate_limit_max = 10
        self.rate_limit_window = 60

    def get_token(self) -> bool:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            resp = requests.post(url, json={
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    self.tenant_access_token = data["tenant_access_token"]
                    self.token_expire_time = int(time.time()) + 7200
                    self._token_fail_count = 0
                    return True
        except Exception as e:
            logger.error(f"获取 token 失败: {e}")
        self._token_fail_count += 1
        if self._token_fail_count >= 3:
            logger.error(f"⚠️ token 获取连续失败 ≥3 次（当前 {self._token_fail_count} 次），请检查凭证/网络")
        return False

    def send(self, open_id: str, text: str):
        if int(time.time()) > self.token_expire_time:
            self.get_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json"
        }
        body = {
            "receive_id": open_id,
            "msg_type": "text",
            "content": json.dumps({"text": text})
        }
        for attempt in range(2):
            try:
                resp = requests.post(url, headers=headers, params={"receive_id_type": "open_id"}, json=body, timeout=30)
                if resp.status_code == 200 and resp.json().get("code") == 0:
                    return True
                logger.error(f"发送失败: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"发送异常: {e}")
            if attempt == 0:
                logger.info("发送失败，重试 1 次（先刷新 token）")
                self.get_token()
        return False

    @staticmethod
    def _strip(text: str) -> str:
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\].*?\x1b\\', '', text)
        return text

    def _run(self, message: str, session_id: str = "") -> tuple[str, str]:
        env = os.environ.copy()
        env.pop("OPENCODE_SERVER_PASSWORD", None)
        env.pop("OPENCODE_SERVER_USERNAME", None)
        cmd = ["opencode", "run", message, "--format", "json", "--dangerously-skip-permissions"]
        if session_id:
            cmd += ["--session", session_id]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(BASE_DIR), env=env)
            stdout = result.stdout or ""
            new_sid = session_id
            text_parts = []
            for line in stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    sid = obj.get("sessionID")
                    if sid:
                        new_sid = sid
                    if obj.get("type") == "text":
                        t = (obj.get("part") or {}).get("text", "")
                        text_parts.append(t)
                except json.JSONDecodeError:
                    pass
            response = "".join(text_parts)
            response = self._strip(response)
            response = re.sub(r'▶️ 下一步：.*', '', response).strip()
            if not response:
                response = self._strip(result.stderr or "") or "（无输出）"
            return response[:15000], new_sid
        except subprocess.TimeoutExpired:
            return "请求超时，请简化问题", session_id
        except FileNotFoundError:
            return "错误：未安装 opencode", session_id
        except Exception as e:
            return f"错误: {e}", session_id

    def _check_rate_limit(self, open_id: str) -> bool:
        """固定窗口限流：窗口内超阈值返回 False（拒绝）。线程安全。"""
        now = time.time()
        with self._rate_lock:
            records = self._rate_limits.get(open_id, [])
            records = [t for t in records if now - t < self.rate_limit_window]
            if len(records) >= self.rate_limit_max:
                self._rate_limits[open_id] = records
                return False
            records.append(now)
            self._rate_limits[open_id] = records
            return True

    def _process(self, event: dict):
        try:
            sender = event.get("event", {}).get("sender", {})
            message = event.get("event", {}).get("message", {})
            open_id = (sender.get("sender_id") or {}).get("open_id", "")
            msg_type = message.get("message_type", "")
            content = message.get("content", "")

            logger.info(f"处理: {open_id} / {msg_type}")

            if msg_type != "text":
                self.send(open_id, "只支持文字消息")
                return

            try:
                text = json.loads(content).get("text", "")
            except json.JSONDecodeError:
                text = content
            text = text.strip()

            if not text:
                return

            if len(text) > 4096:
                logger.warning(f"入站消息超长（{len(text)} 字符）拒绝处理: {open_id}")
                self.send(open_id, "消息过长（超过 4096 字符），请精简后重试")
                return

            if not self._check_rate_limit(open_id):
                logger.warning(f"触发限流（10 条/分钟）: {open_id}")
                self.send(open_id, "消息过于频繁（限 10 条/分钟），请稍后再试")
                return

            session_id = self.sessions.get(open_id, "")
            response, new_sid = self._run(text, session_id)
            if new_sid and new_sid != session_id:
                self.sessions[open_id] = new_sid
            self.send(open_id, response)
        except Exception as e:
            logger.error(f"处理异常: {e}")

    def start(self, port: int = 5103):
        app = Flask(__name__)

        @app.route("/feishu/events", methods=["POST"])
        @app.route("/webhook_sys", methods=["POST"])
        @app.route("/webhook_chat", methods=["POST"])
        def webhook():
            event_data = request.get_json()
            if not event_data:
                return jsonify({"error": "no data"}), 400

            if event_data.get("type") == "url_verification":
                return jsonify({"challenge": event_data.get("challenge", "")})

            if event_data.get("type") != "event_callback":
                return jsonify({"status": "skip"})

            event_type = (event_data.get("event") or {}).get("type", "")
            if event_type != "im.message.receive_v1":
                logger.info(f"跳过事件: {event_type}")
                return jsonify({"status": "skip"})

            msg_id = (event_data.get("event") or {}).get("message", {}).get("message_id", "")
            if msg_id:
                with self._dedup_lock:
                    if msg_id in self._processed_ids:
                        logger.info(f"去重: {msg_id}")
                        return jsonify({"status": "duplicate"})
                    self._processed_ids.add(msg_id)

            threading.Thread(target=self._process, args=(event_data,), daemon=True).start()

            return jsonify({"status": "ok"})

        @app.route("/api/chat", methods=["POST"])
        def api_chat():
            data = request.get_json() or {}
            msg = (data.get("message") or "").strip()
            sid = data.get("session_id") or ""
            if not msg:
                return jsonify({"error": "empty message"}), 400
            if not sid:
                sid = str(uuid.uuid4())
            opencode_sid = self.sessions.get(sid, "")
            response, new_sid = self._run(msg, opencode_sid)
            if new_sid and new_sid != opencode_sid:
                self.sessions[sid] = new_sid
            return jsonify({"response": response, "session_id": sid})

        @app.route("/chat")
        def chat_page():
            html = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>OpenCode</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#1a1a2e;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;height:100vh;display:flex;flex-direction:column}
#header{padding:14px 16px;background:#16213e;border-bottom:1px solid #0f3460;font-size:15px;font-weight:600;color:#e94560;flex-shrink:0;display:flex;align-items:center;gap:8px}
#header span{color:#aaa;font-weight:400;font-size:12px}
#messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;scroll-behavior:smooth}
.msg{max-width:88%;padding:10px 14px;border-radius:10px;line-height:1.6;font-size:14px;white-space:pre-wrap;word-break:break-word}
.msg.user{background:#0f3460;align-self:flex-end;color:#fff}
.msg.bot{background:#16213e;align-self:flex-start;color:#ddd}
.msg.bot.loading{opacity:.6}
.msg.error{background:#3d0000;align-self:flex-start;color:#ff6b6b}
#input_area{display:flex;gap:8px;padding:12px 16px;background:#16213e;border-top:1px solid #0f3460;flex-shrink:0}
#input{flex:1;padding:10px 14px;border:1px solid #0f3460;border-radius:8px;background:#1a1a2e;color:#e0e0e0;font-size:14px;outline:none;resize:none;min-height:42px;max-height:120px;font-family:inherit}
#input:focus{border-color:#e94560}
#send{padding:10px 20px;background:#e94560;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
#send:disabled{opacity:.5;cursor:not-allowed}
code{background:#0d1117;padding:2px 6px;border-radius:4px;font-size:13px;font-family:"SF Mono","Fira Code","Cascadia Code",monospace}
pre{background:#0d1117;padding:12px;border-radius:8px;overflow-x:auto;margin:6px 0}
pre code{background:none;padding:0;font-size:13px;line-height:1.5}
a{color:#e94560}
</style>
</head>
<body>
<div id="header">OpenCode <span>— 编程助手</span></div>
<div id="messages"></div>
<div id="input_area">
<textarea id="input" rows="1" placeholder="输入你的编程问题..."></textarea>
<button id="send" onclick="sendMsg()">发送</button>
</div>
<script>
const el=id=>document.getElementById(id);
const msgs=el('messages');
const inp=el('input');
const btn=el('send');
let sid=localStorage.getItem('oc_sid')||'';
let busy=false;
function addMsg(text,role,extra){
  const d=document.createElement('div');
  d.className='msg '+role+(extra||'');
  d.textContent=text;
  msgs.appendChild(d);
  msgs.scrollTop=msgs.scrollHeight;
  return d;
}
function sendMsg(){
  const msg=inp.value.trim();
  if(!msg||busy) return;
  inp.value='';
  addMsg(msg,'user');
  const ld=addMsg('处理中...','bot loading');
  busy=true;btn.disabled=true;
  fetch('/api/chat',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:msg,session_id:sid})
  }).then(r=>r.json()).then(d=>{
    ld.remove();
    if(d.error){addMsg('错误: '+d.error,'error')}
    else{
      addMsg(d.response,'bot');
      if(d.session_id){sid=d.session_id;localStorage.setItem('oc_sid',sid)}
    }
  }).catch(e=>{
    ld.remove();
    addMsg('连接失败: '+e.message,'error');
  }).finally(()=>{busy=false;btn.disabled=false;inp.focus()});
}
inp.addEventListener('keydown',e=>{
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg()}
});
inp.focus();
</script>
</body>
</html>"""
            return make_response(html, 200, {"Content-Type": "text/html; charset=utf-8"})

        @app.route("/health", methods=["GET"])
        def health():
            return jsonify({"status": "ok"})

        logger.info(f"服务启动于 :{port}")
        app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    config_path = BASE_DIR / "config" / "feishu.yaml"
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    verification_token = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
    port = 5103

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
            if isinstance(cfg, dict):
                app_id = app_id or cfg.get("app_id", "")
                app_secret = app_secret or cfg.get("app_secret", "")
                verification_token = verification_token or cfg.get("verification_token", "")
                port = int(cfg.get("port", port))
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")

    if not app_id or not app_secret:
        logger.error("请在 config/feishu.yaml 中配置 app_id / app_secret")
        sys.exit(1)

    bot = FeishuBot(app_id, app_secret, verification_token)
    if not bot.get_token():
        logger.warning("无法获取飞书 token（凭证未配置或无效），仅 health 检查可用")
    bot.start(port=port)


if __name__ == "__main__":
    main()
