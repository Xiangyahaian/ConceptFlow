"""Fetch East Money concept-board intraday main-force net inflow (fflow kline)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

HOSTS = (
    "push2.eastmoney.com",
    "82.push2.eastmoney.com",
    "push2delay.eastmoney.com",
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://data.eastmoney.com/bkzj/",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 完整交易日约 241 根 1 分钟 K；低于此视为盘中未收完，默认重新拉取
DEFAULT_MIN_FULL_POINTS = 200


def fflow_trade_date(obj: dict) -> str | None:
    """Parse YYYY-MM-DD from first kline timestamp."""
    klines = (obj.get("data") or {}).get("klines") or []
    if not klines:
        return None
    head = str(klines[0]).split(",")[0].strip()
    d = head.split(" ")[0]
    return d if len(d) == 10 else None


def fflow_point_count(obj: dict) -> int:
    klines = (obj.get("data") or {}).get("klines") or []
    return len(klines) if isinstance(klines, list) else 0


def cache_is_fresh(
    obj: dict,
    *,
    today: str,
    min_full: int = DEFAULT_MIN_FULL_POINTS,
) -> bool:
    """
    Keep local cache only when it is today's session and looks complete.
    Older trade dates or incomplete intraday bars must be re-fetched.
    """
    if not is_valid_fflow(obj):
        return False
    d = fflow_trade_date(obj)
    if d != today:
        return False
    return fflow_point_count(obj) >= min_full


def fflow_url(host: str, code: str) -> str:
    return (
        f"https://{host}/api/qt/stock/fflow/kline/get"
        f"?lmt=0&klt=1&secid=90.{code}"
        f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57"
    )


# 沪深两市（上证+深成）分时主力净流入 — 东财「大盘资金流向」同源
MARKET_SECID = "1.000001"
MARKET_SECID2 = "0.399001"
MARKET_RAW_NAME = "fflow_market.json"
MARKET_QUOTE_RAW_NAME = "market_quote.json"
MARKET_TURNOVER_RAW_NAME = "market_turnover_min.json"


def market_fflow_url(host: str) -> str:
    return (
        f"https://{host}/api/qt/stock/fflow/kline/get"
        f"?lmt=0&klt=1&secid={MARKET_SECID}&secid2={MARKET_SECID2}"
        f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57"
    )


def market_quote_url(host: str) -> str:
    # f2 最新价 / f3 涨跌幅 / f6 成交额（元）
    return (
        f"https://{host}/api/qt/ulist.np/get"
        f"?fltt=2&secids={MARKET_SECID},{MARKET_SECID2}"
        f"&fields=f12,f14,f2,f3,f4,f5,f6"
    )


def market_trends_url(host: str, secid: str) -> str:
    # 分时：f51时间 f52开 f53收 f54高 f55低 f56量 f57额 f58均价
    return (
        f"https://{host}/api/qt/stock/trends2/get"
        f"?fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
        f"&iscr=0&ndays=1&secid={secid}"
    )


def fetch_json(url: str, retries: int = 2, sleep: float = 0.8) -> dict:
    last_err: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(sleep * (i + 1))
    raise RuntimeError(f"fetch failed: {url} ({last_err})")


def is_valid_fflow(obj: dict) -> bool:
    data = obj.get("data") or {}
    klines = data.get("klines")
    return isinstance(klines, list) and len(klines) > 10


def fetch_fflow_one(code: str) -> dict:
    last_err: Exception | None = None
    for host in HOSTS:
        try:
            obj = fetch_json(fflow_url(host, code), retries=2, sleep=0.6)
            if is_valid_fflow(obj):
                return obj
            last_err = RuntimeError("empty klines")
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"{code}: {last_err}")


def fetch_market_fflow() -> dict:
    """沪深两市合计主力净流入分时（大盘）。"""
    last_err: Exception | None = None
    for host in HOSTS:
        try:
            obj = fetch_json(market_fflow_url(host), retries=2, sleep=0.6)
            if is_valid_fflow(obj):
                # 标注便于下游识别
                data = obj.setdefault("data", {})
                if isinstance(data, dict):
                    data.setdefault("code", "MARKET")
                    data["name"] = "沪深两市"
                return obj
            last_err = RuntimeError("empty klines")
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"market: {last_err}")


def fetch_market_quote() -> dict:
    """上证+深成报价：合计成交额等。"""
    last_err: Exception | None = None
    for host in HOSTS:
        try:
            obj = fetch_json(market_quote_url(host), retries=2, sleep=0.6)
            diffs = (obj.get("data") or {}).get("diff") or []
            if len(diffs) >= 2:
                return obj
            last_err = RuntimeError("empty quote")
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"market_quote: {last_err}")


def fetch_index_trends(secid: str) -> dict:
    last_err: Exception | None = None
    for host in HOSTS:
        try:
            obj = fetch_json(market_trends_url(host, secid), retries=2, sleep=0.6)
            trends = (obj.get("data") or {}).get("trends") or []
            if len(trends) > 10:
                return obj
            last_err = RuntimeError("empty trends")
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    raise RuntimeError(f"trends {secid}: {last_err}")


def _trends_minute_amount(obj: dict) -> dict[str, float]:
    """time(HH:MM) → 该分钟成交额（元）。"""
    out: dict[str, float] = {}
    for line in (obj.get("data") or {}).get("trends") or []:
        parts = str(line).split(",")
        if len(parts) < 7:
            continue
        stamp = parts[0].strip()
        t = stamp.split(" ")[-1][:5] if " " in stamp else stamp[-5:]
        out[t] = float(parts[6])
    return out


def build_market_turnover_series(sh_obj: dict, sz_obj: dict) -> dict:
    """上证+深成分时成交额累计（亿）。"""
    sh = _trends_minute_amount(sh_obj)
    sz = _trends_minute_amount(sz_obj)
    times = sorted(set(sh) | set(sz))
    cum = 0.0
    series: list[float] = []
    for t in times:
        cum += float(sh.get(t, 0.0)) + float(sz.get(t, 0.0))
        series.append(round(cum / 1e8, 4))
    return {
        "name": "沪深两市",
        "times": times,
        "turnover_yi": series,
        "final_yi": series[-1] if series else 0.0,
        "fetched_at": date.today().isoformat(),
    }


def parse_market_quote(obj: dict) -> dict | None:
    """Parse ulist quote → turnover_yi（两市成交额合计，亿）。"""
    diffs = (obj.get("data") or {}).get("diff") or []
    if len(diffs) < 2:
        return None
    by_code = {str(d.get("f12")): d for d in diffs}
    sh = by_code.get("000001") or diffs[0]
    sz = by_code.get("399001") or diffs[1]
    turnover_yuan = float(sh.get("f6") or 0) + float(sz.get("f6") or 0)
    return {
        "name": "沪深两市",
        "turnover_yi": round(turnover_yuan / 1e8, 2),
        "sh_close": sh.get("f2"),
        "sh_pct": sh.get("f3"),
        "sz_close": sz.get("f2"),
        "sz_pct": sz.get("f3"),
        "fetched_at": date.today().isoformat(),
    }


def download_market_quote(
    raw_dir: Path,
    *,
    force: bool = False,
    use_cache: bool = False,
    today: str | None = None,
) -> bool:
    """Download 两市收盘成交额摘要 + 分时累计成交额。"""
    raw_dir.mkdir(parents=True, exist_ok=True)
    today = today or date.today().isoformat()
    path = raw_dir / MARKET_QUOTE_RAW_NAME
    tpath = raw_dir / MARKET_TURNOVER_RAW_NAME

    quote_ok = False
    if path.exists() and not force:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            parsed = parse_market_quote(obj) if "data" in obj else obj
            if use_cache and parsed and float(parsed.get("turnover_yi") or 0) > 0:
                print(f"  [quote] skip 两市成交额  {parsed['turnover_yi']:.0f}亿")
                quote_ok = True
            elif (
                not use_cache
                and parsed
                and parsed.get("fetched_at") == today
                and float(parsed.get("turnover_yi") or 0) > 0
            ):
                print(f"  [quote] skip 两市成交额  {parsed['turnover_yi']:.0f}亿")
                quote_ok = True
        except Exception:  # noqa: BLE001
            pass
    if not quote_ok:
        try:
            raw = fetch_market_quote()
            parsed = parse_market_quote(raw)
            if not parsed:
                raise RuntimeError("parse quote failed")
            path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [quote] ok   两市成交额 {parsed['turnover_yi']:.2f}亿")
            quote_ok = True
        except Exception as e:  # noqa: BLE001
            print(f"  [quote] FAIL 两市成交额: {e}")

    # 分时累计成交额（供底部文案随时间变化）
    trends_ok = False
    if tpath.exists() and not force:
        try:
            tobj = json.loads(tpath.read_text(encoding="utf-8"))
            series = tobj.get("turnover_yi") or []
            if (
                isinstance(series, list)
                and len(series) > 10
                and (use_cache or tobj.get("fetched_at") == today)
            ):
                print(f"  [turnover] skip 分时成交额  points={len(series)}")
                trends_ok = True
        except Exception:  # noqa: BLE001
            pass
    if not trends_ok:
        try:
            sh = fetch_index_trends(MARKET_SECID)
            sz = fetch_index_trends(MARKET_SECID2)
            packed = build_market_turnover_series(sh, sz)
            tpath.write_text(json.dumps(packed, ensure_ascii=False), encoding="utf-8")
            print(
                f"  [turnover] ok   分时成交额 points={len(packed['turnover_yi'])} "
                f"终值={packed['final_yi']:.2f}亿"
            )
            trends_ok = True
        except Exception as e:  # noqa: BLE001
            print(f"  [turnover] FAIL 分时成交额: {e}")

    return quote_ok or trends_ok


def download_market_fflow(
    raw_dir: Path,
    *,
    force: bool = False,
    use_cache: bool = False,
    min_full: int = DEFAULT_MIN_FULL_POINTS,
    today: str | None = None,
) -> bool:
    """Download / refresh 大盘 fflow JSON，并顺带刷新两市成交额。"""
    raw_dir.mkdir(parents=True, exist_ok=True)
    today = today or date.today().isoformat()
    path = raw_dir / MARKET_RAW_NAME
    ok = False
    if path.exists() and not force:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if use_cache and is_valid_fflow(obj):
                print(f"  [market] skip 沪深两市  ({fflow_trade_date(obj) or '?'})")
                ok = True
            elif not use_cache and cache_is_fresh(obj, today=today, min_full=min_full):
                d = fflow_trade_date(obj) or "?"
                n = fflow_point_count(obj)
                print(f"  [market] skip 沪深两市  ({d}, points={n})")
                ok = True
        except Exception:  # noqa: BLE001
            pass
    if not ok:
        try:
            obj = fetch_market_fflow()
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            d = fflow_trade_date(obj) or "?"
            n = fflow_point_count(obj)
            final = 0.0
            klines = (obj.get("data") or {}).get("klines") or []
            if klines:
                parts = str(klines[-1]).split(",")
                if len(parts) >= 2:
                    final = float(parts[1]) / 1e8
            print(f"  [market] ok   沪深两市  date={d} points={n} 净流入={final:+.2f}亿")
            ok = True
        except Exception as e:  # noqa: BLE001
            print(f"  [market] FAIL 沪深两市: {e}")
            ok = False

    # 成交额接口很轻，非 use_cache 时每次刷新，保证底部数字是收盘值
    download_market_quote(
        raw_dir,
        force=(not use_cache) or force,
        use_cache=use_cache,
        today=today,
    )
    return ok


def load_boards(boards_file: Path) -> list[dict]:
    return json.loads(boards_file.read_text(encoding="utf-8"))


def download_boards_fflow(
    boards: list[dict],
    raw_dir: Path,
    *,
    force: bool = False,
    use_cache: bool = False,
    pause: float = 0.12,
    min_full: int = DEFAULT_MIN_FULL_POINTS,
    today: str | None = None,
) -> tuple[list[str], list[str]]:
    """Download fflow JSON for each board. Returns (ok_codes, failed_codes).

    Cache policy (unless force=True):
    - Default: only reuse a file when它是「今天」且点数已接近完整日。
    - use_cache=True: 只要本地 JSON 合法就跳过（旧行为，易卡住旧交易日）。
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    today = today or date.today().isoformat()
    ok: list[str] = []
    failed: list[str] = []
    skipped = 0
    refreshed_stale = 0
    for i, b in enumerate(boards, 1):
        code = b["code"]
        path = raw_dir / f"fflow_{code}.json"
        if path.exists() and not force:
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                if use_cache and is_valid_fflow(obj):
                    ok.append(code)
                    skipped += 1
                    print(f"  [{i}/{len(boards)}] skip {code} {b.get('name','')}")
                    continue
                if not use_cache and cache_is_fresh(obj, today=today, min_full=min_full):
                    ok.append(code)
                    skipped += 1
                    d = fflow_trade_date(obj) or "?"
                    n = fflow_point_count(obj)
                    print(
                        f"  [{i}/{len(boards)}] skip {code} {b.get('name','')}"
                        f"  ({d}, points={n})"
                    )
                    continue
                if is_valid_fflow(obj) and not use_cache:
                    refreshed_stale += 1
                    d = fflow_trade_date(obj) or "?"
                    n = fflow_point_count(obj)
                    print(
                        f"  [{i}/{len(boards)}] refresh {code} {b.get('name','')}"
                        f"  (缓存 {d}/{n}点 → 重新拉取)"
                    )
            except Exception:  # noqa: BLE001
                pass
        try:
            obj = fetch_fflow_one(code)
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            ok.append(code)
            n = fflow_point_count(obj)
            d = fflow_trade_date(obj) or "?"
            print(
                f"  [{i}/{len(boards)}] ok   {code} {b.get('name','')}"
                f"  date={d} points={n}"
            )
        except Exception as e:  # noqa: BLE001
            failed.append(code)
            print(f"  [{i}/{len(boards)}] FAIL {code} {b.get('name','')}: {e}")
        time.sleep(pause)

    if skipped or refreshed_stale or force:
        print(
            f"[fetch] 缓存策略: today={today} force={force} use_cache={use_cache} "
            f"skip={skipped} refresh_stale={refreshed_stale}"
        )

    # one more retry round for failures
    if failed:
        print(f"[fetch] retry {len(failed)} failed…")
        still: list[str] = []
        for code in failed:
            path = raw_dir / f"fflow_{code}.json"
            try:
                obj = fetch_fflow_one(code)
                path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                ok.append(code)
                print(f"  retry ok {code}")
            except Exception as e:  # noqa: BLE001
                still.append(code)
                print(f"  retry fail {code}: {e}")
            time.sleep(0.25)
        failed = still
    return ok, failed


def peek_data_date(raw_dir: Path) -> str | None:
    """Infer trade date from any raw fflow file (prefer the newest trade date)."""
    dates: list[str] = []
    for path in sorted(raw_dir.glob("fflow_BK*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            d = fflow_trade_date(obj)
            if d:
                dates.append(d)
        except Exception:  # noqa: BLE001
            continue
    return max(dates) if dates else None


def peek_point_count(raw_dir: Path) -> int:
    counts = []
    for path in raw_dir.glob("fflow_BK*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            n = fflow_point_count(obj)
            if n:
                counts.append(n)
        except Exception:  # noqa: BLE001
            continue
    return min(counts) if counts else 0
