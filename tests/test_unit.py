"""
模块名称：test_unit
功能描述：FeishuBot 单元测试——覆盖 M4 T2-T5 新增逻辑（C9 截断/C10 限流/C11 入站校验/C12 重试告警）
对外接口：
    - main()：运行全部测试
依赖：
    - 标准库：os, sys, json, time, unittest.mock
    - 项目内：src.feishu_integration.FeishuBot
版本：v1.0
更新记录：
    - 2026-08-05: 初始创建，覆盖 C9/C10/C11/C12
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

from feishu_integration import FeishuBot


def make_bot() -> FeishuBot:
    return FeishuBot("test_app_id", "test_app_secret")


class TestC9Truncate(unittest.TestCase):
    """C9 输出截断代码块保护"""

    def test_short_text_unchanged(self):
        bot = make_bot()
        s = "正常输出" * 100
        self.assertEqual(bot._truncate(s), s)

    def test_inside_code_block_dropped(self):
        bot = make_bot()
        out = bot._truncate("```python\n" + "x = 1\n" * 6000 + "```\n" + "tail")
        self.assertNotIn("tail", out)
        self.assertTrue(out.endswith("（内容已截断）"))
        self.assertNotIn("x = 1", out)

    def test_full_block_preserved(self):
        bot = make_bot()
        block = "```python\nprint(1)\n```\n"
        out = bot._truncate(block + "long" * 6000)
        self.assertTrue(out.startswith("```python\nprint(1)\n```"))

    def test_unclosed_block_dropped(self):
        bot = make_bot()
        out = bot._truncate("```md\nstart\n" + "y\n" * 8000)
        self.assertTrue(out.endswith("（内容已截断）"))
        self.assertNotIn("start", out)


class TestC10RateLimit(unittest.TestCase):
    """C10 open_id 固定窗口限流（10 条/分）"""

    def test_window_allows_max(self):
        bot = make_bot()
        for _ in range(10):
            self.assertTrue(bot._check_rate_limit("ou_a"))

    def test_exceeds_rejected(self):
        bot = make_bot()
        for _ in range(10):
            bot._check_rate_limit("ou_a")
        self.assertFalse(bot._check_rate_limit("ou_a"))

    def test_per_open_id_isolated(self):
        bot = make_bot()
        for _ in range(10):
            bot._check_rate_limit("ou_a")
        self.assertTrue(bot._check_rate_limit("ou_b"))

    def test_window_slides_reset(self):
        bot = make_bot()
        bot._rate_limits["ou_a"] = [time.time() - 61] * 10
        self.assertTrue(bot._check_rate_limit("ou_a"))


class TestC11InputValidation(unittest.TestCase):
    """C11 入站 4KB 校验（4096 字符拒绝）"""

    def _process_event(self, bot, text, msg_type="text"):
        event = {
            "event": {
                "sender": {"sender_id": {"open_id": "ou_v"}},
                "message": {"message_type": msg_type, "content": json.dumps({"text": text})},
            }
        }
        bot._process(event)

    @patch.object(FeishuBot, "send")
    def test_overlong_rejected(self, msend):
        bot = make_bot()
        self._process_event(bot, "a" * 5000)
        self.assertTrue(msend.called)
        self.assertIn("消息过长", msend.call_args[0][1])

    @patch.object(FeishuBot, "send")
    def test_normal_text_processed(self, msend):
        bot = make_bot()
        with patch.object(bot, "_run", return_value=("回复", "sid1")):
            self._process_event(bot, "你好")
        self.assertTrue(msend.called)
        self.assertEqual(msend.call_args[0][1], "回复")

    @patch.object(FeishuBot, "send")
    def test_non_text_rejected(self, msend):
        bot = make_bot()
        self._process_event(bot, "{}", msg_type="image")
        self.assertTrue(msend.called)
        self.assertIn("只支持文字消息", msend.call_args[0][1])


class TestC12SendRetryTokenAlert(unittest.TestCase):
    """C12 发送失败重试 1 次 + token 连续失败≥3 告警"""

    @patch.object(FeishuBot, "get_token", return_value=True)
    def test_retry_once_then_success(self, mtoken):
        bot = make_bot()
        bot.tenant_access_token = "t1"
        bot.token_expire_time = int(time.time()) + 3600
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"code": 0}
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        fail_resp.text = "err"
        with patch("requests.post", side_effect=[fail_resp, ok_resp]) as mpost:
            self.assertTrue(bot.send("ou_z", "hello"))
        self.assertEqual(mpost.call_count, 2)
        self.assertEqual(mtoken.call_count, 1)

    def test_token_fail_alerts_at_three(self):
        bot = make_bot()
        with patch("requests.post", side_effect=Exception("net")) as mpost:
            bot.get_token()
            bot.get_token()
            bot.get_token()
        self.assertEqual(bot._token_fail_count, 3)
        self.assertEqual(mpost.call_count, 3)

    def test_token_success_resets_counter(self):
        bot = make_bot()
        bot._token_fail_count = 2
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"code": 0, "tenant_access_token": "tok"}
        with patch("requests.post", return_value=ok_resp):
            self.assertTrue(bot.get_token())
        self.assertEqual(bot._token_fail_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
