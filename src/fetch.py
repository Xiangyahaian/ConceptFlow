"""Fetch East Money concept-board intraday main-force net inflow (fflow kline)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
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


def fflow_url(host: str, code: str) -> str:
    return (
        f"https://{host}/api/qt/stock/fflow/kline/get"
        f"?lmt=0&klt=1&secid=90.{code}"
        f"&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57"
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


def load_boards(boards_file: Path) -> list[dict]:
    return json.loads(boards_file.read_text(encoding="utf-8"))


def download_boards_fflow(
    boards: list[dict],
    raw_dir: Path,
    *,
    force: bool = False,
    pause: float = 0.12,
) -> tuple[list[str], list[str]]:
    """Download fflow JSON for each board. Returns (ok_codes, failed_codes)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    ok: list[str] = []
    failed: list[str] = []
    for i, b in enumerate(boards, 1):
        code = b["code"]
        path = raw_dir / f"fflow_{code}.json"
        if path.exists() and not force:
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
                if is_valid_fflow(obj):
                    ok.append(code)
                    print(f"  [{i}/{len(boards)}] skip {code} {b.get('name','')}")
                    continue
            except Exception:  # noqa: BLE001
                pass
        try:
            obj = fetch_fflow_one(code)
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            ok.append(code)
            n = len((obj.get("data") or {}).get("klines") or [])
            print(f"  [{i}/{len(boards)}] ok   {code} {b.get('name','')}  points={n}")
        except Exception as e:  # noqa: BLE001
            failed.append(code)
            print(f"  [{i}/{len(boards)}] FAIL {code} {b.get('name','')}: {e}")
        time.sleep(pause)

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
    """Infer trade date from any raw fflow file."""
    for path in sorted(raw_dir.glob("fflow_BK*.json")):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            klines = (obj.get("data") or {}).get("klines") or []
            if not klines:
                continue
            # "2026-08-10 09:31,...."
            head = str(klines[0]).split(",")[0].strip()
            date = head.split(" ")[0]
            if len(date) == 10:
                return date
        except Exception:  # noqa: BLE001
            continue
    return None


def peek_point_count(raw_dir: Path) -> int:
    counts = []
    for path in raw_dir.glob("fflow_BK*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            klines = (obj.get("data") or {}).get("klines") or []
            if klines:
                counts.append(len(klines))
        except Exception:  # noqa: BLE001
            continue
    return min(counts) if counts else 0
