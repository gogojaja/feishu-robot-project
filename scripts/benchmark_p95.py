"""
模块名称：benchmark_p95
功能描述：端到端 P95 性能基准补测——通过桥接服务真实调用 opencode 模型推理，统计 P50/P95/P99 延迟
对外接口：
    - main()：运行 20 次请求并输出百分位延迟统计
依赖：
    - 标准库：os, sys, json, time, statistics, subprocess, pathlib
    - 项目内：无（直接调用 opencode CLI）
版本：v1.0
更新记录：
    - 2026-08-07: 初始创建，补测 ARCH-DEF-002 端到端 P95
"""

import os
import sys
import json
import time
import statistics
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_MSG = "ping"
ROUNDS = 20


def run_once(msg: str, session_id: str = "") -> tuple[float, str]:
    """执行一次端到端桥接调用，返回 (耗时秒, 新 session_id)"""
    env = os.environ.copy()
    env.pop("OPENCODE_SERVER_PASSWORD", None)
    env.pop("OPENCODE_SERVER_USERNAME", None)
    cmd = [
        "opencode", "run", msg, "--format", "json",
        "--model", "opencode/deepseek-v4-flash-free",
        "--attach", "http://127.0.0.1:5102",
    ]
    if session_id:
        cmd += ["--session", session_id]
    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(BASE_DIR), env=env)
        elapsed = time.time() - start
        return elapsed, result.stdout or ""
    except subprocess.TimeoutExpired:
        return 180.0, ""


def percentile(sorted_vals: list, p: float) -> float:
    """线性插值百分位"""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[-1]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def main():
    print("=" * 60)
    print(f"端到端 P95 性能基准补测（{ROUNDS} 次）")
    print("=" * 60)
    latencies = []
    for i in range(1, ROUNDS + 1):
        elapsed, _ = run_once(TEST_MSG)
        latencies.append(elapsed)
        print(f"  第 {i:2d} 次: {elapsed:.1f}s")
        time.sleep(0.5)

    sorted_lat = sorted(latencies)
    p50 = percentile(sorted_lat, 0.50)
    p95 = percentile(sorted_lat, 0.95)
    p99 = percentile(sorted_lat, 0.99)
    avg = statistics.mean(latencies)
    mx = max(latencies)

    print("\n" + "=" * 60)
    print("统计结果")
    print("=" * 60)
    print(f"  平均: {avg:.1f}s")
    print(f"  P50:  {p50:.1f}s")
    print(f"  P95:  {p95:.1f}s")
    print(f"  P99:  {p99:.1f}s")
    print(f"  Max:  {mx:.1f}s")
    print(f"  超时(≥180s): {sum(1 for v in latencies if v >= 180)} 次")

    result = {
        "rounds": ROUNDS,
        "avg_s": round(avg, 2),
        "p50_s": round(p50, 2),
        "p95_s": round(p95, 2),
        "p99_s": round(p99, 2),
        "max_s": round(mx, 2),
        "timeouts": sum(1 for v in latencies if v >= 180),
        "all": [round(v, 2) for v in latencies],
    }
    out = BASE_DIR / "var" / "benchmark_p95_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已保存: {out}")
    print("=" * 60)


if __name__ == "__main__":
    main()
