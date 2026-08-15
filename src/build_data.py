"""Merge raw East Money fflow JSON into the Manim scene pack."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.fetch import MARKET_QUOTE_RAW_NAME, MARKET_RAW_NAME, MARKET_TURNOVER_RAW_NAME


def _display_name(name: str) -> str:
    return (name or "").replace("概念", "")


def format_turnover_yi(turnover_yi: float) -> str:
    """25509亿 → 2.55万亿；较小则保留亿。"""
    yi = float(turnover_yi)
    if yi >= 10000:
        return f"{yi / 10000:.2f}万亿"
    if yi >= 100:
        return f"{yi:.0f}亿"
    return f"{yi:.1f}亿"


def market_punch_text(net_yi: float, turnover_yi: float | None = None) -> str:
    """底部摘要：大盘净流入/净流出 + 两市成交额（同一行）。"""
    if net_yi >= 0:
        flow = f"大盘净流入 {net_yi:+.1f}亿"
    else:
        flow = f"大盘净流出 {abs(net_yi):.1f}亿"
    if turnover_yi is None or turnover_yi <= 0:
        return flow
    return f"{flow}    成交额 {format_turnover_yi(turnover_yi)}"


def _align_series_to_times(
    src_times: list[str],
    src_vals: list[float],
    target_times: list[str],
) -> list[float]:
    """按目标时刻对齐；缺时刻用前值（或首值）填。"""
    if not src_times or not src_vals or not target_times:
        return []
    mp = {t: float(v) for t, v in zip(src_times, src_vals)}
    out: list[float] = []
    last: float | None = None
    first = float(src_vals[0])
    for t in target_times:
        if t in mp:
            last = mp[t]
        out.append(last if last is not None else first)
    return out


def parse_fflow(path: Path) -> dict | None:
    obj = json.loads(path.read_text(encoding="utf-8"))
    data = obj.get("data") or {}
    klines = data.get("klines") or []
    if len(klines) < 10:
        return None
    times: list[str] = []
    flow: list[float] = []
    trade_date: str | None = None
    for line in klines:
        parts = str(line).split(",")
        if len(parts) < 2:
            continue
        stamp = parts[0].strip()
        if " " in stamp:
            d, t = stamp.split(" ", 1)
            if trade_date is None:
                trade_date = d
            times.append(t[:5])
        else:
            times.append(stamp[-5:])
        flow.append(float(parts[1]) / 1e8)
    if not flow:
        return None
    return {
        "code": data.get("code") or path.stem.replace("fflow_", ""),
        "name": data.get("name") or "",
        "times": times,
        "flow_yi": flow,
        "final_yi": flow[-1],
        "trade_date": trade_date,
    }


def title_for_date(date_str: str) -> str:
    """2026-08-10 -> 8月10日收盘资金流向"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.month}月{dt.day}日收盘资金流向"


def build_pack(
    boards: list[dict],
    raw_dir: Path,
    out_file: Path,
    *,
    date: str | None = None,
) -> dict:
    series: list[dict] = []
    for item in boards:
        code = item["code"]
        path = raw_dir / f"fflow_{code}.json"
        if not path.exists():
            print(f"  missing raw: {code} {item.get('name','')}")
            continue
        s = parse_fflow(path)
        if not s:
            print(f"  bad raw: {code}")
            continue
        # Prefer the curated Chinese name from boards.json
        s["name"] = item.get("name") or s["name"]
        series.append(s)

    if not series:
        raise SystemExit("没有可用的板块分时数据，请先拉取 API。")

    n = int(min(len(s["flow_yi"]) for s in series))
    times = series[0]["times"][:n]
    if date is None:
        date = next((s.get("trade_date") for s in series if s.get("trade_date")), None)
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    pack = {
        "date": date,
        "title": title_for_date(date),
        "unit": "yi",
        "n_points": n,
        "times": times,
        "boards": [
            {
                "code": s["code"],
                "name": _display_name(s["name"]),
                "final_yi": round(s["flow_yi"][n - 1], 2),
                "flow_yi": [round(x, 4) for x in s["flow_yi"][:n]],
            }
            for s in series
        ],
    }
    pack["boards"].sort(key=lambda b: b["final_yi"])

    market_path = raw_dir / MARKET_RAW_NAME
    market = parse_fflow(market_path) if market_path.exists() else None

    turnover_final: float | None = None
    turnover_series: list[float] = []
    tpath = raw_dir / MARKET_TURNOVER_RAW_NAME
    if tpath.exists():
        try:
            tobj = json.loads(tpath.read_text(encoding="utf-8"))
            t_times = tobj.get("times") or []
            t_vals = tobj.get("turnover_yi") or []
            if t_times and t_vals:
                turnover_series = [
                    round(x, 4)
                    for x in _align_series_to_times(t_times, t_vals, times)
                ]
                turnover_final = round(turnover_series[-1], 2) if turnover_series else None
        except Exception as e:  # noqa: BLE001
            print(f"[build] 警告: 读取分时成交额失败: {e}")

    if turnover_final is None:
        quote_path = raw_dir / MARKET_QUOTE_RAW_NAME
        if quote_path.exists():
            try:
                q = json.loads(quote_path.read_text(encoding="utf-8"))
                if "turnover_yi" in q and not isinstance(q["turnover_yi"], list):
                    turnover_final = float(q["turnover_yi"])
                else:
                    from src.fetch import parse_market_quote

                    parsed = parse_market_quote(q)
                    if parsed:
                        turnover_final = float(parsed["turnover_yi"])
            except Exception as e:  # noqa: BLE001
                print(f"[build] 警告: 读取成交额失败: {e}")

    if market:
        flow_aligned = _align_series_to_times(market["times"], market["flow_yi"], times)
        if not flow_aligned:
            flow_aligned = [float(x) for x in market["flow_yi"][:n]]
            while len(flow_aligned) < n:
                flow_aligned.append(flow_aligned[-1])
            flow_aligned = flow_aligned[:n]
        net = round(flow_aligned[-1], 2)
        if not turnover_series and turnover_final is not None:
            # 无分时则整段用终值（退化）
            turnover_series = [float(turnover_final)] * n
        pack["market"] = {
            "name": "沪深两市",
            "final_yi": net,
            "turnover_yi": turnover_final if turnover_final is not None else (
                round(turnover_series[-1], 2) if turnover_series else None
            ),
            "flow_yi": [round(x, 4) for x in flow_aligned],
            "turnover_series_yi": turnover_series,
            "punch": market_punch_text(
                net,
                turnover_final
                if turnover_final is not None
                else (turnover_series[-1] if turnover_series else None),
            ),
        }
    else:
        pack["market"] = None
        print("[build] 警告: 缺少大盘 fflow，底部将无净流入/流出摘要")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

    bot, top = pack["boards"][0], pack["boards"][-1]
    print(f"[build] date={date} boards={len(pack['boards'])} points={n}")
    print(f"[build] title={pack['title']}")
    print(f"[build] 板块流入TOP {top['name']} {top['final_yi']:+.2f}")
    print(f"[build] 板块流出TOP {bot['name']} {bot['final_yi']:+.2f}")
    if pack.get("market"):
        print(f"[build] 大盘 {pack['market']['punch']}")
    print(f"[build] -> {out_file}")
    return pack
