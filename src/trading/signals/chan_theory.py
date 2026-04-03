# -*- coding: utf-8 -*-
"""
Chan Theory (缠论) Analysis Module

Implements the complete Chan Theory computational pipeline:
  分型 (Fractal) → 笔 (Stroke) → 中枢 (Hub) → 背驰 (Divergence) → 买卖点 (Buy/Sell Points)

K-line data must include: date, open, high, low, close, MACD_BAR columns.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Data Structures
# ============================================================

@dataclass
class MergedKLine:
    """K-line after containment processing (包含处理)"""
    index: int          # position in merged array
    orig_start: int     # first original bar index
    orig_end: int       # last original bar index
    open: float
    high: float
    low: float
    close: float
    direction: int      # +1 uptrend merge, -1 downtrend merge
    merged_count: int   # how many original bars were merged


@dataclass
class Fractal:
    """Top or bottom fractal (顶分型/底分型)"""
    index: int          # index in merged K-line array
    fractal_type: str   # "top" or "bottom"
    high: float
    low: float
    orig_index: int     # index in original DataFrame


@dataclass
class Stroke:
    """Stroke (笔) connecting two fractals"""
    start: Fractal
    end: Fractal
    direction: int      # +1 = up (bottom→top), -1 = down (top→bottom)
    high: float
    low: float
    bar_count: int      # merged K-lines between start and end


@dataclass
class Hub:
    """Hub / Center (中枢)"""
    strokes: List[Stroke]
    ZG: float           # min of entering stroke highs (upper overlap boundary)
    ZD: float           # max of entering stroke lows (lower overlap boundary)
    high: float         # highest point in hub
    low: float          # lowest point in hub
    start_idx: int      # original df index of hub start
    end_idx: int        # original df index of hub end


@dataclass
class ChanAnalysisResult:
    """Complete Chan Theory analysis result"""
    merged_klines: List[MergedKLine]
    fractals: List[Fractal]
    strokes: List[Stroke]
    hubs: List[Hub]
    buy_points: List[Dict]
    sell_points: List[Dict]


# ============================================================
# Chan Theory Analyzer
# ============================================================

class ChanTheoryAnalyzer:
    """
    Full Chan Theory analysis engine.

    Pipeline: merge K-lines → detect fractals → build strokes →
              build hubs → detect MACD divergence → identify buy/sell points
    """

    def __init__(
        self,
        min_stroke_bars: int = 4,
        min_hub_strokes: int = 3,
    ):
        self.min_stroke_bars = min_stroke_bars
        self.min_hub_strokes = min_hub_strokes

    # ----------------------------------------------------------
    # Step A: K-line containment processing (包含处理)
    # ----------------------------------------------------------
    def _merge_klines(self, df: pd.DataFrame) -> List[MergedKLine]:
        """Merge K-lines with containment relationships."""
        if df.empty:
            return []

        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        closes = df["close"].values

        merged: List[MergedKLine] = []
        for i in range(len(df)):
            merged.append(MergedKLine(
                index=i, orig_start=i, orig_end=i,
                open=float(opens[i]), high=float(highs[i]),
                low=float(lows[i]), close=float(closes[i]),
                direction=0, merged_count=1,
            ))

        # Multi-pass merge until stable
        changed = True
        while changed:
            changed = False
            new_merged: List[MergedKLine] = []
            i = 0
            while i < len(merged):
                if i == 0:
                    new_merged.append(merged[i])
                    i += 1
                    continue

                prev = new_merged[-1]
                curr = merged[i]

                # Check containment: one bar contains the other
                prev_contains_curr = (prev.high >= curr.high and prev.low <= curr.low)
                curr_contains_prev = (curr.high >= prev.high and curr.low <= prev.low)

                if prev_contains_curr or curr_contains_prev:
                    # Determine merge direction from trend
                    if len(new_merged) >= 2:
                        direction = 1 if new_merged[-1].high > new_merged[-2].high else -1
                    else:
                        direction = 1 if curr.close >= prev.close else -1

                    if direction >= 0:
                        # Uptrend: keep higher high and higher low
                        new_high = max(prev.high, curr.high)
                        new_low = max(prev.low, curr.low)
                    else:
                        # Downtrend: keep lower high and lower low
                        new_high = min(prev.high, curr.high)
                        new_low = min(prev.low, curr.low)

                    new_merged[-1] = MergedKLine(
                        index=prev.index,
                        orig_start=prev.orig_start,
                        orig_end=curr.orig_end,
                        open=prev.open,
                        high=new_high,
                        low=new_low,
                        close=curr.close,
                        direction=direction,
                        merged_count=prev.merged_count + curr.merged_count,
                    )
                    changed = True
                else:
                    new_merged.append(curr)
                i += 1
            merged = new_merged

        # Re-index
        for idx, m in enumerate(merged):
            m.index = idx

        return merged

    # ----------------------------------------------------------
    # Step B: Fractal detection (分型识别)
    # ----------------------------------------------------------
    def _detect_fractals(self, merged: List[MergedKLine]) -> List[Fractal]:
        """Detect top and bottom fractals from merged K-lines."""
        if len(merged) < 3:
            return []

        fractals: List[Fractal] = []
        for i in range(1, len(merged) - 1):
            prev, curr, next_ = merged[i - 1], merged[i], merged[i + 1]

            # Top fractal: high > both neighbors
            if curr.high > prev.high and curr.high > next_.high:
                fractals.append(Fractal(
                    index=i, fractal_type="top",
                    high=curr.high, low=curr.low,
                    orig_index=curr.orig_end,
                ))
            # Bottom fractal: low < both neighbors
            elif curr.low < prev.low and curr.low < next_.low:
                fractals.append(Fractal(
                    index=i, fractal_type="bottom",
                    high=curr.high, low=curr.low,
                    orig_index=curr.orig_end,
                ))

        return fractals

    # ----------------------------------------------------------
    # Step C: Stroke construction (笔构造)
    # ----------------------------------------------------------
    def _build_strokes(self, fractals: List[Fractal]) -> List[Stroke]:
        """Build strokes by connecting alternating top/bottom fractals."""
        if len(fractals) < 2:
            return []

        strokes: List[Stroke] = []
        last_fractal = fractals[0]

        for i in range(1, len(fractals)):
            curr = fractals[i]

            # Must alternate type
            if curr.fractal_type == last_fractal.fractal_type:
                # Same type: keep the more extreme one
                if curr.fractal_type == "top":
                    if curr.high > last_fractal.high:
                        last_fractal = curr
                else:
                    if curr.low < last_fractal.low:
                        last_fractal = curr
                continue

            # Check minimum distance
            bar_count = curr.index - last_fractal.index
            if bar_count < self.min_stroke_bars:
                continue

            # Build stroke
            if last_fractal.fractal_type == "bottom" and curr.fractal_type == "top":
                direction = 1  # up stroke
            else:
                direction = -1  # down stroke

            stroke = Stroke(
                start=last_fractal, end=curr,
                direction=direction,
                high=max(last_fractal.high, curr.high),
                low=min(last_fractal.low, curr.low),
                bar_count=bar_count,
            )
            strokes.append(stroke)
            last_fractal = curr

        return strokes

    # ----------------------------------------------------------
    # Step D: Hub construction (中枢识别)
    # ----------------------------------------------------------
    def _build_hubs(self, strokes: List[Stroke]) -> List[Hub]:
        """Build hubs from overlapping strokes."""
        if len(strokes) < self.min_hub_strokes:
            return []

        hubs: List[Hub] = []
        i = 0
        while i <= len(strokes) - self.min_hub_strokes:
            # Try to form a hub starting from stroke i
            # Take first 3 strokes
            s1, s2, s3 = strokes[i], strokes[i + 1], strokes[i + 2]

            # Hub overlap: ZG = min of highs, ZD = max of lows
            ZG = min(s1.high, s2.high, s3.high)
            ZD = max(s1.low, s2.low, s3.low)

            if ZG <= ZD:
                # No valid overlap
                i += 1
                continue

            hub_strokes = [s1, s2, s3]
            hub_high = max(s1.high, s2.high, s3.high)
            hub_low = min(s1.low, s2.low, s3.low)

            # Extend hub with subsequent strokes that overlap
            j = i + 3
            while j < len(strokes):
                s = strokes[j]
                # Stroke overlaps with hub if it passes through [ZD, ZG]
                if s.high >= ZD and s.low <= ZG:
                    hub_strokes.append(s)
                    hub_high = max(hub_high, s.high)
                    hub_low = min(hub_low, s.low)
                    j += 1
                else:
                    break

            hub = Hub(
                strokes=hub_strokes,
                ZG=ZG, ZD=ZD,
                high=hub_high, low=hub_low,
                start_idx=s1.start.orig_index,
                end_idx=hub_strokes[-1].end.orig_index,
            )
            hubs.append(hub)
            i = j  # skip past this hub's strokes

        return hubs

    # ----------------------------------------------------------
    # Step E: MACD area divergence (背驰判断)
    # ----------------------------------------------------------
    def _compute_macd_area(
        self, macd_bar: np.ndarray, start_idx: int, end_idx: int
    ) -> float:
        """Sum MACD_BAR values between two indices (absolute area)."""
        start = max(0, start_idx)
        end = min(len(macd_bar), end_idx + 1)
        segment = macd_bar[start:end]
        return float(np.sum(np.abs(segment)))

    def _detect_divergences(
        self, df: pd.DataFrame, strokes: List[Stroke]
    ) -> Dict[int, str]:
        """
        Detect MACD divergences between consecutive same-direction strokes.
        Returns: dict mapping stroke index to divergence type ("top"/"bottom").
        """
        divergences: Dict[int, str] = {}
        if len(strokes) < 3 or "MACD_BAR" not in df.columns:
            return divergences

        macd_bar = df["MACD_BAR"].fillna(0).values
        close = df["close"].values

        for i in range(2, len(strokes)):
            curr = strokes[i]
            # Find the previous stroke with same direction
            prev = None
            for j in range(i - 2, -1, -2):
                if strokes[j].direction == curr.direction:
                    prev = strokes[j]
                    break

            if prev is None:
                continue

            curr_area = self._compute_macd_area(
                macd_bar, curr.start.orig_index, curr.end.orig_index
            )
            prev_area = self._compute_macd_area(
                macd_bar, prev.start.orig_index, prev.end.orig_index
            )

            if prev_area == 0:
                continue

            # Bottom divergence: current makes lower low but MACD area is smaller
            if curr.direction == -1:
                curr_low = curr.low
                prev_low = prev.low
                if curr_low < prev_low and curr_area < prev_area:
                    divergences[i] = "bottom"

            # Top divergence: current makes higher high but MACD area is smaller
            elif curr.direction == 1:
                curr_high = curr.high
                prev_high = prev.high
                if curr_high > prev_high and curr_area < prev_area:
                    divergences[i] = "top"

        return divergences

    # ----------------------------------------------------------
    # Step F: Buy/Sell point detection (买卖点判定)
    # ----------------------------------------------------------
    def _detect_buy_sell_points(
        self,
        strokes: List[Stroke],
        hubs: List[Hub],
        divergences: Dict[int, str],
        df: pd.DataFrame,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Detect Chan Theory buy and sell points."""
        buy_points: List[Dict] = []
        sell_points: List[Dict] = []

        if not strokes or not hubs:
            return buy_points, sell_points

        close = df["close"].values

        # --- First Buy (一买): Bottom divergence at end of downtrend ---
        for stroke_idx, div_type in divergences.items():
            if div_type != "bottom":
                continue
            stroke = strokes[stroke_idx]
            # Check if this stroke is after a hub
            for hub in hubs:
                if stroke.end.orig_index > hub.end_idx and stroke.low <= hub.low:
                    buy_points.append({
                        "type": "first_buy",
                        "bar_index": stroke.end.orig_index,
                        "price": stroke.end.low,
                        "fractal_low": stroke.end.low,
                        "hub_ZG": hub.ZG,
                        "hub_ZD": hub.ZD,
                        "divergence": True,
                        "num_hubs": len(hubs),
                        "reason": f"底背驰一买, 中枢[{hub.ZD:.2f}-{hub.ZG:.2f}]",
                    })
                    break

        # --- Second Buy (二买): Pullback doesn't break hub ZG after up-break ---
        for i, hub in enumerate(hubs):
            # Find strokes after this hub
            post_hub_strokes = [
                s for s in strokes
                if s.start.orig_index >= hub.end_idx
            ]
            if len(post_hub_strokes) < 2:
                continue

            # First stroke after hub goes up, second pulls back
            first_after = post_hub_strokes[0]
            if first_after.direction != 1:
                continue
            if first_after.high <= hub.ZG:
                continue  # didn't break above hub

            second_after = post_hub_strokes[1]
            if second_after.direction != -1:
                continue

            # Pullback low stays above hub ZD (relaxed: above hub ZG is strict 二买)
            if second_after.low >= hub.ZD:
                buy_points.append({
                    "type": "second_buy",
                    "bar_index": second_after.end.orig_index,
                    "price": second_after.end.low,
                    "fractal_low": second_after.end.low,
                    "hub_ZG": hub.ZG,
                    "hub_ZD": hub.ZD,
                    "divergence": False,
                    "num_hubs": len(hubs),
                    "reason": f"二买, 回调低点{second_after.low:.2f} > 中枢ZD{hub.ZD:.2f}",
                })

        # --- Third Buy (三买): Break above hub, pullback stays above ZG ---
        for i, hub in enumerate(hubs):
            post_hub_strokes = [
                s for s in strokes
                if s.start.orig_index >= hub.end_idx
            ]
            if len(post_hub_strokes) < 2:
                continue

            first_after = post_hub_strokes[0]
            if first_after.direction != 1 or first_after.high <= hub.ZG:
                continue

            second_after = post_hub_strokes[1]
            if second_after.direction != -1:
                continue

            # Strict third buy: pullback low stays above ZG
            if second_after.low > hub.ZG:
                buy_points.append({
                    "type": "third_buy",
                    "bar_index": second_after.end.orig_index,
                    "price": second_after.end.low,
                    "fractal_low": second_after.end.low,
                    "hub_ZG": hub.ZG,
                    "hub_ZD": hub.ZD,
                    "divergence": False,
                    "num_hubs": len(hubs),
                    "reason": f"三买, 回调低点{second_after.low:.2f} > 中枢ZG{hub.ZG:.2f}",
                })

        # --- First Sell (一卖): Top divergence at end of uptrend ---
        for stroke_idx, div_type in divergences.items():
            if div_type != "top":
                continue
            stroke = strokes[stroke_idx]
            for hub in hubs:
                if stroke.end.orig_index > hub.end_idx and stroke.high >= hub.high:
                    sell_points.append({
                        "type": "first_sell",
                        "bar_index": stroke.end.orig_index,
                        "price": stroke.end.high,
                        "fractal_high": stroke.end.high,
                        "hub_ZG": hub.ZG,
                        "hub_ZD": hub.ZD,
                        "divergence": True,
                        "reason": f"顶背驰一卖, 中枢[{hub.ZD:.2f}-{hub.ZG:.2f}]",
                    })
                    break

        # --- Second Sell (二卖): Bounce doesn't break hub ZD after down-break ---
        for i, hub in enumerate(hubs):
            post_hub_strokes = [
                s for s in strokes
                if s.start.orig_index >= hub.end_idx
            ]
            if len(post_hub_strokes) < 2:
                continue

            first_after = post_hub_strokes[0]
            if first_after.direction != -1 or first_after.low >= hub.ZD:
                continue

            second_after = post_hub_strokes[1]
            if second_after.direction != 1:
                continue

            if second_after.high <= hub.ZG:
                sell_points.append({
                    "type": "second_sell",
                    "bar_index": second_after.end.orig_index,
                    "price": second_after.end.high,
                    "fractal_high": second_after.end.high,
                    "hub_ZG": hub.ZG,
                    "hub_ZD": hub.ZD,
                    "divergence": False,
                    "reason": f"二卖, 反弹高点{second_after.high:.2f} < 中枢ZG{hub.ZG:.2f}",
                })

        # --- Third Sell (三卖): Break below hub, bounce stays below ZD ---
        for i, hub in enumerate(hubs):
            post_hub_strokes = [
                s for s in strokes
                if s.start.orig_index >= hub.end_idx
            ]
            if len(post_hub_strokes) < 2:
                continue

            first_after = post_hub_strokes[0]
            if first_after.direction != -1 or first_after.low >= hub.ZD:
                continue

            second_after = post_hub_strokes[1]
            if second_after.direction != 1:
                continue

            if second_after.high < hub.ZD:
                sell_points.append({
                    "type": "third_sell",
                    "bar_index": second_after.end.orig_index,
                    "price": second_after.end.high,
                    "fractal_high": second_after.end.high,
                    "hub_ZG": hub.ZG,
                    "hub_ZD": hub.ZD,
                    "divergence": False,
                    "reason": f"三卖, 反弹高点{second_after.high:.2f} < 中枢ZD{hub.ZD:.2f}",
                })

        # Sort by bar_index
        buy_points.sort(key=lambda x: x["bar_index"])
        sell_points.sort(key=lambda x: x["bar_index"])

        return buy_points, sell_points

    # ----------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------
    def analyze(self, df: pd.DataFrame) -> ChanAnalysisResult:
        """Run the complete Chan Theory analysis pipeline."""
        if df.empty or len(df) < 10:
            return ChanAnalysisResult([], [], [], [], [], [])

        merged = self._merge_klines(df)
        fractals = self._detect_fractals(merged)
        strokes = self._build_strokes(fractals)
        hubs = self._build_hubs(strokes)
        divergences = self._detect_divergences(df, strokes)
        buy_points, sell_points = self._detect_buy_sell_points(
            strokes, hubs, divergences, df
        )

        return ChanAnalysisResult(
            merged_klines=merged,
            fractals=fractals,
            strokes=strokes,
            hubs=hubs,
            buy_points=buy_points,
            sell_points=sell_points,
        )
