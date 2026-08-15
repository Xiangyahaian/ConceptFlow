"""Concept board fund-flow overlay — labels appear at 11:00 and smoothly track tips."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from manim import *

# 竖屏默认 2K（1440×2560）；可用环境变量升到 4K / 改帧率
config.pixel_width = int(os.environ.get("FUND_FLOW_PIXEL_WIDTH", "1440"))
config.pixel_height = int(os.environ.get("FUND_FLOW_PIXEL_HEIGHT", "2560"))
config.frame_rate = int(os.environ.get("FUND_FLOW_FPS", "30"))
config.frame_width = 9
config.frame_height = 16

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATA = _ROOT / "data" / "concept_fflow_major.json"
DATA = Path(os.environ.get("FUND_FLOW_DATA", str(_DEFAULT_DATA)))


def _cn_font() -> str:
    env = os.environ.get("FUND_FLOW_CN_FONT", "").strip()
    if env:
        return env
    if sys.platform == "darwin":
        return "PingFang SC"
    if sys.platform.startswith("linux"):
        return "Noto Sans CJK SC"
    return "Microsoft YaHei"


CN_FONT = _cn_font()

# 竖屏构图：外框再收一档，手机四周留白更大
FRAME_W = 7.35
FRAME_H = 11.70
PAD_L = 0.20
PAD_R = 0.20
PAD_TB = 0.36
YLAB_W = 0.78
GAP_YLAB_PLOT = 0.08
GAP_PLOT_PILL = 0.14
PILL_W = 2.40
# 右侧标签：字号优先放大；框高=文字高+内边距
PILL_PAD_Y = 0.16
PILL_MIN_H = 0.36

# 轴/单位/底部摘要字号（标题保持原样）
AXIS_FONT = 18
PUNCH_FONT = 24
PUNCH_FONT_COMPACT = 22

# 分时曲线动画时长；右侧标签 + 底部大盘文案在开始后约 1s 淡入
DAY_ANIM_SEC = 11.0
LABEL_APPEAR_AFTER_SEC = 1.0


def cn(text: str, **kwargs) -> Text:
    return Text(text, font=CN_FONT, **kwargs)


def load_pack() -> dict:
    if not DATA.exists():
        raise FileNotFoundError(f"缺少数据: {DATA}")
    return json.loads(DATA.read_text(encoding="utf-8"))


def color_for_flow(final: float, lo: float, hi: float) -> ManimColor:
    if final >= 0:
        t = float(np.clip(final / max(hi, 1e-6), 0, 1))
        return interpolate_color(ORANGE, RED, 0.25 + 0.75 * t)
    t = float(np.clip(final / min(lo, -1e-6), 0, 1))
    if t < 0.45:
        return interpolate_color(YELLOW_E, TEAL, t / 0.45)
    return interpolate_color(TEAL, GREEN_E, (t - 0.45) / 0.55)


def make_pill(name: str, val: float, color: ManimColor, font_size: int, width: float) -> VGroup:
    txt = cn(f"{name} {val:+.2f}", font_size=font_size, color=color)
    if txt.width > width - 0.20:
        txt.scale((width - 0.20) / txt.width)
    box = RoundedRectangle(
        corner_radius=0.10,
        width=width,
        height=max(txt.height + PILL_PAD_Y, PILL_MIN_H),
        stroke_color=color,
        stroke_width=1.8,
        fill_color="#121212",
        fill_opacity=0.95,
    )
    g = VGroup(box, txt)
    txt.move_to(box.get_center())
    g.name_str = name  # type: ignore[attr-defined]
    g.font_size = font_size  # type: ignore[attr-defined]
    g.pill_w = width  # type: ignore[attr-defined]
    g.last_val = float(val)  # type: ignore[attr-defined]
    g.pill_color = color  # type: ignore[attr-defined]
    return g


def apply_pill_opacity(pill: VGroup, opacity: float) -> None:
    """Set box+text opacity without dropping Text from the scene graph."""
    op = float(np.clip(opacity, 0.0, 1.0))
    pill[0].set_stroke(opacity=op)
    pill[0].set_fill(opacity=0.95 * op)
    pill[1].set_opacity(op)


def format_turnover_yi(turnover_yi: float) -> str:
    yi = float(turnover_yi)
    if yi >= 10000:
        return f"{yi / 10000:.2f}万亿"
    if yi >= 100:
        return f"{yi:.0f}亿"
    return f"{yi:.1f}亿"


def market_punch_text(net_yi: float, turnover_yi: float | None = None) -> str:
    if net_yi >= 0:
        flow = f"大盘净流入 {net_yi:+.1f}亿"
    else:
        flow = f"大盘净流出 {abs(net_yi):.1f}亿"
    if turnover_yi is None or turnover_yi <= 0:
        return flow
    return f"{flow}    成交额 {format_turnover_yi(turnover_yi)}"


def refresh_punch(
    punch: Text,
    net_yi: float,
    turnover_yi: float | None,
    *,
    font_size: int,
    opacity: float = 1.0,
    last_net: float | None = None,
    last_to: float | None = None,
) -> tuple[float, float | None]:
    """Update bottom market summary text; returns (net, turnover) actually shown."""
    to = None if turnover_yi is None else float(turnover_yi)
    # 避免每帧 become：净流入变 0.8 亿或成交额变 30 亿再刷
    if last_net is not None and abs(net_yi - last_net) < 0.8:
        if to is None or last_to is None or abs(to - last_to) < 30.0:
            punch.set_opacity(opacity)
            return last_net, last_to
    color = ORANGE if net_yi >= 0 else TEAL
    txt = market_punch_text(net_yi, to)
    new = cn(txt, font_size=font_size, color=color)
    new.move_to(punch.get_center())
    punch.become(new)
    punch.set_opacity(opacity)
    return float(net_yi), to


def refresh_pill_text(pill: VGroup, val: float, color: ManimColor, opacity: float = 1.0) -> None:
    """Update label text via become (keeps Text renderable)."""
    if abs(val - pill.last_val) < 0.25 and color == getattr(pill, "pill_color", None):
        apply_pill_opacity(pill, opacity)
        return
    pill.last_val = float(val)
    pill.pill_color = color
    new_txt = cn(f"{pill.name_str} {val:+.2f}", font_size=pill.font_size, color=color)
    if new_txt.width > pill.pill_w - 0.20:
        new_txt.scale((pill.pill_w - 0.20) / new_txt.width)
    new_txt.move_to(pill[0].get_center())
    pill[1].become(new_txt)
    pill[0].set_stroke(color=color)
    apply_pill_opacity(pill, opacity)


def fixed_slot_ys(m: int, y_lo: float, y_hi: float, item_h: float) -> np.ndarray:
    """Immutable rank rails, bottom→top. Full pill stays inside [y_lo, y_hi], no overlap."""
    edge = 0.08  # air gap to band edge (keeps bottom pill clear of x-axis)
    # Center of lowest/highest pill so box edges clear y_lo / y_hi
    bottom = y_lo + item_h * 0.5 + edge
    top = y_hi - item_h * 0.5 - edge
    if m <= 1:
        return np.array([0.5 * (y_lo + y_hi)], dtype=float)
    if top <= bottom:
        mid = 0.5 * (y_lo + y_hi)
        return np.full(m, mid, dtype=float)
    # Prefer even spacing; if band is tight, pack to exactly touch (no overlap)
    span = top - bottom
    min_span = item_h * (m - 1)
    if span < min_span:
        # Shrink effective height so m slots still fit without leaving the band
        ih = span / (m - 1)
        bottom = y_lo + ih * 0.5 + edge
        top = y_hi - ih * 0.5 - edge
    return np.linspace(bottom, top, m)


def ranks_to_slot_ys(values: np.ndarray, slot_ys: np.ndarray) -> np.ndarray:
    """Each board → fixed slot by current rank (low value → bottom slot)."""
    _, ys = sticky_rank_slot_ys(values, slot_ys, prev_rank=None, margin=0.0)
    return ys


def sticky_rank_slot_ys(
    values: np.ndarray,
    slot_ys: np.ndarray,
    prev_rank: np.ndarray | None,
    margin: float = 1.2,
) -> tuple[np.ndarray, np.ndarray]:
    """Map boards to fixed rails with hysteresis so near-ties don't thrash/overlap."""
    m = len(values)
    if prev_rank is None:
        order = np.argsort(values, kind="mergesort")
    else:
        order = np.argsort(prev_rank, kind="mergesort").astype(int)
        # Neighbor swaps only when clearly crossed (margin in 亿)
        changed = True
        while changed:
            changed = False
            for j in range(m - 1):
                a, b = int(order[j]), int(order[j + 1])
                if values[a] > values[b] + margin:
                    order[j], order[j + 1] = b, a
                    changed = True
    rank = np.empty(m, dtype=int)
    rank[order] = np.arange(m)
    return rank, slot_ys[rank]


def build_chrome(scene: Scene) -> dict:
    """Title / frame / axes / ticks — shared by still & animation."""
    scene.camera.background_color = "#050505"
    pack = load_pack()
    boards = pack["boards"]
    times = pack["times"]
    n = int(pack["n_points"])
    xs = np.linspace(0.0, 1.0, n)

    finals = np.array([b["final_yi"] for b in boards], dtype=float)
    lo, hi = float(np.min(finals)), float(np.max(finals))
    all_y = np.concatenate([np.array(b["flow_yi"], dtype=float) for b in boards])
    # Auto Y scale from today's curves (keeps 0 in view, nice tick step)
    raw_min = float(np.min(all_y))
    raw_max = float(np.max(all_y))
    pad = max(8.0, 0.06 * max(raw_max - raw_min, 1.0))
    y_min = min(raw_min - pad, -5.0)
    y_max = max(raw_max + pad, 5.0)
    span = y_max - y_min
    if span >= 250:
        y_step = 50
    elif span >= 120:
        y_step = 20
    elif span >= 60:
        y_step = 10
    else:
        y_step = 5
    y_min = float(np.floor(y_min / y_step) * y_step)
    y_max = float(np.ceil(y_max / y_step) * y_step)

    title = cn(pack.get("title") or "收盘资金流向", font_size=42, color=YELLOW)
    title.to_edge(UP, buff=0.78)

    frame = RoundedRectangle(
        corner_radius=0.16,
        width=FRAME_W,
        height=FRAME_H,
        stroke_color=GREY_A,
        stroke_width=2.4,
        fill_color="#0a0a0a",
        fill_opacity=0.5,
    )
    frame.next_to(title, DOWN, buff=0.40)
    accent = RoundedRectangle(
        corner_radius=0.16,
        width=FRAME_W,
        height=FRAME_H,
        stroke_color=YELLOW,
        stroke_width=1.0,
        fill_opacity=0,
    ).move_to(frame)
    accent.set_stroke(opacity=0.35)

    inner_left = frame.get_left()[0] + PAD_L
    inner_right = frame.get_right()[0] - PAD_R
    inner_bottom = frame.get_bottom()[1] + PAD_TB
    inner_top = frame.get_top()[1] - PAD_TB

    plot_w = (inner_right - inner_left) - YLAB_W - GAP_YLAB_PLOT - GAP_PLOT_PILL - PILL_W
    plot_h = inner_top - inner_bottom - 0.35
    y_axis_x = inner_left + YLAB_W + GAP_YLAB_PLOT
    plot_center_x = y_axis_x + plot_w / 2
    plot_center_y = (inner_bottom + 0.32 + inner_top) / 2

    axes = Axes(
        x_range=[0, 1, 0.25],
        y_range=[y_min, y_max, y_step],
        x_length=plot_w,
        y_length=plot_h,
        axis_config={"color": GREY_B, "stroke_width": 1.4},
        tips=False,
    )
    axes.move_to([plot_center_x, plot_center_y, 0])
    axes.shift(RIGHT * (y_axis_x - axes.c2p(0, 0)[0]))

    zero = axes.plot(lambda x: 0, x_range=[0, 1], color=GREY_A, stroke_width=1.6)
    unit = cn("亿", font_size=AXIS_FONT, color=GREY_A)
    unit.next_to(axes.c2p(0, y_max), RIGHT, buff=0.12)
    unit.shift(DOWN * 0.18)

    ylab = VGroup()
    y0 = int(np.ceil(y_min / y_step) * y_step)
    y1 = int(np.floor(y_max / y_step) * y_step)
    for yv in range(y0, y1 + 1, y_step):
        if abs(yv) < 1e-9:
            text, col = "0", WHITE
        elif yv > 0:
            text, col = f"+{yv}", ORANGE
        else:
            text, col = f"{yv}", TEAL
        lab = cn(text, font_size=AXIS_FONT, color=col)
        lab.next_to(axes.c2p(0, yv), LEFT, buff=0.10)
        ylab.add(lab)

    xlab = VGroup()
    for lab, forced in [("09:30", 0.0), ("11:30", None), ("14:00", None), ("15:00", 1.0)]:
        if forced is not None:
            xv = forced
        else:
            idxs = [i for i, t in enumerate(times) if t == lab]
            if not idxs:
                continue
            xv = float(xs[idxs[0]])
        t = Text(lab, font_size=AXIS_FONT, color=GREY_A)
        t.next_to(axes.c2p(xv, y_min), DOWN, buff=0.14)
        xlab.add(t)

    colors = [color_for_flow(float(b["final_yi"]), lo, hi) for b in boards]
    series_y = [np.array(b["flow_yi"], dtype=float) for b in boards]

    # 右侧标签带：底部必须高于横坐标时刻文字，避免「小金属」等垫底标签压住 09:30
    xlab_top = float(max(m.get_top()[1] for m in xlab)) if len(xlab) else inner_bottom
    pill_y0 = max(inner_bottom + 0.22, xlab_top + 0.16)
    pill_y1 = inner_top - 0.18
    avail = pill_y1 - pill_y0
    edge = 0.06
    min_gap = 0.028  # air between stacked pills (keeps swaps readable)
    # 优先更大字号；外框变矮后仍尽量保住可读性
    font_size, gap, item_h = 12, 0.02, 0.36
    for fs, g in (
        (17, 0.030),
        (16, 0.028),
        (15, 0.026),
        (14, 0.024),
        (13, 0.022),
        (12, 0.020),
        (11, 0.018),
    ):
        sample = make_pill("通信技术", -308.34, GREY_A, fs, PILL_W)
        ih = sample.height
        need = ih * len(boards) + min_gap * (len(boards) - 1) + 2 * edge
        if need <= avail:
            font_size, gap, item_h = fs, g, ih
            break

    pill_cx = inner_right - PILL_W / 2
    # 约 LABEL_APPEAR_AFTER_SEC 秒（相对分时动画）对应的数据下标
    appear_idx = int(
        np.clip(
            round(LABEL_APPEAR_AFTER_SEC / DAY_ANIM_SEC * max(n - 1, 1)),
            1,
            max(n - 1, 1),
        )
    )

    # 底部摘要：与右侧标签同步出现，并随分时净流入/成交额变化
    market = pack.get("market") or {}
    m_flow = [float(x) for x in (market.get("flow_yi") or [])]
    m_turn = [float(x) for x in (market.get("turnover_series_yi") or [])]
    while len(m_flow) < n and m_flow:
        m_flow.append(m_flow[-1])
    while len(m_turn) < n and m_turn:
        m_turn.append(m_turn[-1])
    m_flow = m_flow[:n] if m_flow else [float(market.get("final_yi") or 0.0)] * n
    if not m_turn:
        tf = float(market.get("turnover_yi") or 0.0)
        m_turn = [tf] * n if tf > 0 else []

    appear_net = float(m_flow[appear_idx]) if m_flow else float(market.get("final_yi") or 0.0)
    appear_to = float(m_turn[appear_idx]) if m_turn else (
        float(market["turnover_yi"]) if market.get("turnover_yi") is not None else None
    )
    punch_str = market_punch_text(appear_net, appear_to)
    punch_fs = PUNCH_FONT_COMPACT if appear_to else PUNCH_FONT
    punch_color = ORANGE if appear_net >= 0 else TEAL
    punch = cn(punch_str, font_size=punch_fs, color=punch_color)
    punch.next_to(frame, DOWN, buff=0.40)
    punch.set_opacity(0)

    scene.add(title, frame, accent, axes, zero, unit, xlab, ylab)

    return {
        "boards": boards,
        "times": times,
        "n": n,
        "xs": xs,
        "series_y": series_y,
        "axes": axes,
        "colors": colors,
        "lo": lo,
        "hi": hi,
        "font_size": font_size,
        "gap": gap,
        "item_h": item_h,
        "pill_y0": pill_y0,
        "pill_y1": pill_y1,
        "pill_cx": pill_cx,
        "appear_idx": appear_idx,
        "frame": frame,
        "punch": punch,
        "punch_fs": punch_fs,
        "market_flow": m_flow,
        "market_turnover": m_turn,
        "title": title,
    }


class FundFlowStill(Scene):
    def construct(self):
        info = build_chrome(self)
        boards = info["boards"]
        n = info["n"]
        xs = info["xs"]
        axes = info["axes"]
        m = len(boards)
        vals = np.array([s[-1] for s in info["series_y"]], dtype=float)
        sample_pills = [
            make_pill(b["name"], float(b["final_yi"]), info["colors"][i], info["font_size"], PILL_W)
            for i, b in enumerate(boards)
        ]
        real_h = max(float(p.height) for p in sample_pills)
        slot_ys = fixed_slot_ys(m, info["pill_y0"], info["pill_y1"], real_h)
        ys_pos = ranks_to_slot_ys(vals, slot_ys)

        for i, b in enumerate(boards):
            ys = info["series_y"][i]
            col = info["colors"][i]
            w = 2.6 if abs(ys[-1]) > 80 else (2.0 if abs(ys[-1]) > 20 else 1.4)
            pts = [axes.c2p(float(xs[j]), float(ys[j])) for j in range(n)]
            line = VMobject(stroke_color=col, stroke_width=w)
            line.set_points_as_corners(pts)
            tip = Dot(pts[-1], radius=0.03, color=col)
            pill = sample_pills[i]
            pill.move_to([info["pill_cx"], ys_pos[i], 0])
            apply_pill_opacity(pill, 1.0)
            leader = Line(pts[-1], pill.get_left() + LEFT * 0.03, stroke_color=col, stroke_width=1.0)
            leader.set_stroke(opacity=0.45)
            self.add(line, tip, leader, pill)

        info["punch"].set_opacity(1)
        # 静帧用收盘值
        m_flow = info.get("market_flow") or []
        m_turn = info.get("market_turnover") or []
        net = float(m_flow[-1]) if m_flow else 0.0
        to = float(m_turn[-1]) if m_turn else None
        refresh_punch(
            info["punch"],
            net,
            to,
            font_size=int(info.get("punch_fs") or 22),
            opacity=1.0,
        )
        self.add(info["punch"])
        self.wait(0.1)


class FundFlowOverlay(Scene):
    """Curves grow; from 11:00 labels appear. Slot rails fixed; pills swap ranks smoothly."""

    def construct(self):
        info = build_chrome(self)
        boards = info["boards"]
        n = info["n"]
        xs = info["xs"]
        axes = info["axes"]
        m = len(boards)
        appear = info["appear_idx"]

        # Precompute all screen points once (avoids axes.c2p × boards × frames)
        path_pts: list[list] = []
        for i in range(m):
            ys = info["series_y"][i]
            path_pts.append([axes.c2p(float(xs[j]), float(ys[j])) for j in range(n)])

        curves: list[VMobject] = []
        tips: list[Dot] = []
        leaders: list[Line] = []
        pills: list[VGroup] = []
        pill_cx = float(info["pill_cx"])
        leader_x = pill_cx - PILL_W / 2 - 0.03
        for i, b in enumerate(boards):
            ys = info["series_y"][i]
            col = info["colors"][i]
            w = 2.6 if abs(ys[-1]) > 80 else (2.0 if abs(ys[-1]) > 20 else 1.4)
            p0, p1 = path_pts[i][0], path_pts[i][1]
            line = VMobject(stroke_color=col, stroke_width=w)
            line.set_points_as_corners([p0, p1])
            tip = Dot(p1, radius=0.035, color=col)
            pill = make_pill(b["name"], float(ys[appear]), col, info["font_size"], PILL_W)
            apply_pill_opacity(pill, 0.0)
            leader = Line(p1, [leader_x, 0, 0], stroke_color=col, stroke_width=1.1)
            leader.set_stroke(opacity=0)
            curves.append(line)
            tips.append(tip)
            leaders.append(leader)
            pills.append(pill)
            self.add(line, tip, leader, pill)

        # Fixed rank rails from real pill height — rails never move; pills swap into them
        real_h = max(float(p.height) for p in pills)
        slot_ys = fixed_slot_ys(m, info["pill_y0"], info["pill_y1"], real_h)
        slot_step = float(slot_ys[1] - slot_ys[0]) if m > 1 else real_h
        init_vals = np.array([info["series_y"][j][appear] for j in range(m)], dtype=float)
        init_slot_y = ranks_to_slot_ys(init_vals, slot_ys)
        for i, pill in enumerate(pills):
            pill.move_to([pill_cx, float(init_slot_y[i]), 0])

        self.add(info["punch"])

        tracker = ValueTracker(1.0)
        # display y for each pill (eases toward its current rank's fixed rail)
        smooth_y = init_slot_y.copy()
        init_rank, _ = sticky_rank_slot_ys(init_vals, slot_ys, prev_rank=None, margin=0.0)
        series_y = info["series_y"]
        colors = info["colors"]
        m_flow = info.get("market_flow") or []
        m_turn = info.get("market_turnover") or []
        punch_fs = int(info.get("punch_fs") or 22)
        state = {
            "smooth_y": smooth_y,
            "ready": False,
            "slot_step": slot_step,
            "rank": init_rank,
            "last_k": -1,
            "labels_hidden": False,
            "tip_pts": [path_pts[i][1] for i in range(m)],
            "last_fade": -1.0,
            "last_y": smooth_y.copy(),
            "punch_net": None,
            "punch_to": None,
        }

        def sync_frame():
            k = int(round(tracker.get_value()))
            k = max(1, min(k, n - 1))
            # Curves only rebuild when sample index advances
            k_changed = k != state["last_k"]
            if k_changed:
                tip_pts = []
                for i in range(m):
                    pts = path_pts[i][: k + 1]
                    curves[i].set_points_as_corners(pts)
                    tips[i].move_to(pts[-1])
                    tip_pts.append(pts[-1])
                state["tip_pts"] = tip_pts
                state["last_k"] = k
            else:
                tip_pts = state["tip_pts"]

            if k < appear:
                if not state["labels_hidden"]:
                    for i in range(m):
                        apply_pill_opacity(pills[i], 0.0)
                        leaders[i].set_stroke(opacity=0)
                    info["punch"].set_opacity(0)
                    state["labels_hidden"] = True
                return

            state["labels_hidden"] = False
            fade = float(np.clip((k - appear) / 8.0, 0.0, 1.0))
            vals = np.array([series_y[i][k] for i in range(m)], dtype=float)
            # Rank only when data index moves (swap still lerps every frame)
            if k != state.get("rank_k", -1):
                rank, target = sticky_rank_slot_ys(vals, slot_ys, state["rank"], margin=1.2)
                state["rank"] = rank
                state["target"] = target
                state["rank_k"] = k
            else:
                target = state["target"]

            if not state["ready"]:
                state["smooth_y"] = target.copy()
                state["ready"] = True
            else:
                delta = target - state["smooth_y"]
                dist = np.abs(delta) / max(state["slot_step"], 1e-6)
                alpha = np.clip(0.12 + 0.32 * dist, 0.12, 0.48)
                state["smooth_y"] = state["smooth_y"] + alpha * delta

            fade_changed = abs(fade - state["last_fade"]) > 0.02
            state["last_fade"] = fade

            # 底部大盘：与标签同节奏淡入，数值跟当前分时走
            if m_flow:
                net_k = float(m_flow[min(k, len(m_flow) - 1)])
                to_k = float(m_turn[min(k, len(m_turn) - 1)]) if m_turn else None
                if k_changed or state["punch_net"] is None:
                    state["punch_net"], state["punch_to"] = refresh_punch(
                        info["punch"],
                        net_k,
                        to_k,
                        font_size=punch_fs,
                        opacity=fade,
                        last_net=state["punch_net"],
                        last_to=state["punch_to"],
                    )
                elif fade_changed:
                    info["punch"].set_opacity(fade)

            for i in range(m):
                col = colors[i]
                y = float(state["smooth_y"][i])
                moved = abs(y - float(state["last_y"][i])) > 1e-3
                if moved:
                    pills[i].move_to([pill_cx, y, 0])
                    state["last_y"][i] = y
                if fade_changed or abs(vals[i] - pills[i].last_val) >= 0.5:
                    refresh_pill_text(pills[i], float(vals[i]), col, opacity=fade)
                elif fade_changed:
                    apply_pill_opacity(pills[i], fade)
                if moved or fade_changed or k_changed:
                    leaders[i].put_start_and_end_on(tip_pts[i], [leader_x, y, 0])
                    leaders[i].set_stroke(color=col, opacity=0.55 * fade)

        curves[0].add_updater(lambda mob: sync_frame())
        sync_frame()
        self.wait(0.25)
        self.play(
            tracker.animate.set_value(float(n - 1)),
            run_time=DAY_ANIM_SEC,
            rate_func=linear,
        )

        curves[0].clear_updaters()
        # lock to final ranks on fixed slots
        for i in range(m):
            pts = path_pts[i]
            curves[i].set_points_as_corners(pts)
            tips[i].move_to(pts[-1])

        vals = np.array([s[-1] for s in series_y], dtype=float)
        final_ys = ranks_to_slot_ys(vals, slot_ys)
        anims = []
        for i in range(m):
            refresh_pill_text(pills[i], float(vals[i]), colors[i], opacity=1.0)
            anims.append(pills[i].animate.move_to([pill_cx, float(final_ys[i]), 0]))
        self.play(*anims, run_time=0.65, rate_func=smooth)
        for i in range(m):
            y = float(final_ys[i])
            leaders[i].put_start_and_end_on(path_pts[i][-1], [leader_x, y, 0])
            leaders[i].set_stroke(opacity=0.55)

        # 收盘值锁定底部文案
        net_f = float(m_flow[-1]) if m_flow else 0.0
        to_f = float(m_turn[-1]) if m_turn else None
        refresh_punch(info["punch"], net_f, to_f, font_size=punch_fs, opacity=1.0)
        self.wait(6.3)
