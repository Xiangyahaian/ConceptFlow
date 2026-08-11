"""Merge raw East Money fflow JSON into the Manim scene pack."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _display_name(name: str) -> str:
    return (name or "").replace("概念", "")


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
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

    bot, top = pack["boards"][0], pack["boards"][-1]
    print(f"[build] date={date} boards={len(pack['boards'])} points={n}")
    print(f"[build] title={pack['title']}")
    print(f"[build] 流入TOP {top['name']} {top['final_yi']:+.2f}")
    print(f"[build] 流出TOP {bot['name']} {bot['final_yi']:+.2f}")
    print(f"[build] -> {out_file}")
    return pack
