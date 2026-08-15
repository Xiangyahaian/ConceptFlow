"""Decide whether fetched data matches 'today', and ask the user if not."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def today_cn() -> date:
    """Calendar today in local time (user is expected to be CN)."""
    return date.today()


def parse_ymd(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def explain_mismatch(data_date: date, today: date, n_points: int, min_full: int) -> str:
    lines = [
        f"接口返回的数据日期为：{data_date.isoformat()}",
        f"今天日历日期为：      {today.isoformat()}",
    ]
    if data_date == today:
        if n_points < min_full:
            lines.append(
                f"点数仅 {n_points}（完整日约 {min_full}+），可能仍在盘中，曲线尚未收完。"
            )
        else:
            lines.append("日期一致，数据看起来是完整交易日。")
        return "\n".join(lines)

    if is_weekend(today):
        lines.append("今天是周末，A股休市，接口通常返回上一交易日。")
    elif data_date < today:
        lines.append(
            "今日分时可能尚未更新（盘前/节假日/接口延迟），"
            "当前拿到的是上一交易日（或更早）数据。"
        )
    else:
        lines.append("数据日期晚于今天（少见，请核对系统时间）。")
    return "\n".join(lines)


def confirm_use_data(
    data_date_str: str,
    *,
    n_points: int,
    min_full: int = 200,
    assume_yes: bool = False,
) -> bool:
    """
    Return True if we should proceed with this data.
    If data_date != today (or incomplete), ask the user unless assume_yes.
    """
    data_date = parse_ymd(data_date_str)
    today = today_cn()
    msg = explain_mismatch(data_date, today, n_points, min_full)
    print("\n======== 数据日期检查 ========")
    print(msg)
    print("================================\n")

    needs_ask = data_date != today or n_points < min_full
    if not needs_ask:
        return True

    if assume_yes:
        print(
            f"[date] --yes：继续使用交易日 {data_date.isoformat()} "
            f"（点数 {n_points}）生成视频。"
        )
        return True

    if data_date != today:
        prompt = (
            f"接口仍是 {data_date.isoformat()}（不是今天 {today.isoformat()}）。"
            f"是否用这份数据生成视频？ [Y/n] "
        )
    else:
        prompt = (
            f"数据可能仍在盘中（点数 {n_points}）。是否仍用当前数据生成视频？ [Y/n] "
        )

    try:
        ans = input(prompt).strip().lower()
    except EOFError:
        ans = "y"
    if ans in ("", "y", "yes", "是", "好", "ok"):
        return True
    print("已取消。可稍后再运行，或使用：python run.py --sample")
    return False


def previous_calendar_day(d: date | None = None) -> date:
    d = d or today_cn()
    return d - timedelta(days=1)
