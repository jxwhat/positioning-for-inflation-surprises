"""Chart helpers for the study's recurring exhibit shapes, in Plotly.

Every helper returns a ``plotly.graph_objects.Figure``. Pass ``fig=`` (from
:func:`subplots`) plus ``row``/``col`` to draw into one panel of a larger figure
instead. Figures render interactively in Jupyter and VS Code; with the renderer
that :func:`use_house_style` selects, each output also carries a static PNG, so
the committed notebook still shows its charts on GitHub and in PDF exports.

Palette and mark rules follow the house data-viz method: colour follows the
entity (a sleeve keeps its hue in every chart), a diverging red<->blue pair with
a neutral gray midpoint for polarity, recessive chrome, thin marks, series
identified by direct labels or a legend (never colour alone), and value labels
on bars.

Theme: a dark, Bloomberg-terminal look — bright marks on black, amber as the
lead hue, dim grid. Inflation regimes use a red<->blue diverging pair rather
than red/green, the one distinction roughly 8% of men cannot make.

Palette validation (OKLab ΔE ×100, dark surface #000000, all pairs):
* traditional assets  orange / cyan / pink        — CVD 11.6, normal-vision 16.5: PASS
* real assets         green / yellow / magenta / white — CVD 17.0, normal-vision 19.7: PASS
* metric legs         orange / white / cyan       — CVD 21.2, normal-vision 27.0: PASS
* regime pair         red / blue                  — CVD 23.1, normal-vision 34.7: PASS
The lightness-band and chroma checks fail by design: terminal styling puts
full-brightness hues (and white as a series) on pure black.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

AMBER = "#ff8c00"
WHITE = "#f2f2f2"
CYAN = "#29b6f6"
PINK = "#ff80ab"
GREEN = "#4caf50"
YELLOW = "#ffd600"
MAGENTA = "#e040fb"
RED = "#ff5252"

#: Fallback hues, fixed order, for series without an entry in SERIES_COLOURS.
CATEGORICAL = [AMBER, WHITE, CYAN, GREEN, YELLOW, MAGENTA, PINK, RED]

#: The three metric legs.
LEG_COLOURS = {"change": AMBER, "surprise": WHITE, "combined": CYAN}

#: Colour follows the entity: a sleeve keeps its hue in every chart.
SERIES_COLOURS = {
    **LEG_COLOURS,
    "equities": AMBER,
    "ust_10y": CYAN,
    "sixty_forty": PINK,
    "commodities": GREEN,
    "gold": YELLOW,
    "precious_metals": WHITE,
    "reits": MAGENTA,
    "portfolio": WHITE,
    "headline CPI": AMBER,
    "core CPI": WHITE,
}

#: Diverging polarity: red for upside surprises, blue for downside, gray between.
POLARITY = {"upside": RED, "stable": "#8c8c8c", "downside": CYAN}
POLARITY_ORDER = ["upside", "stable", "downside"]

#: Presentation labels for the panel's column names.
DISPLAY_NAMES = {
    "equities": "US equities",
    "ust_5y": "UST 5y",
    "ust_10y": "UST 10y",
    "ust_20y": "UST 20y",
    "sixty_forty": "60/40",
    "commodities": "Commodities",
    "gold": "Gold",
    "precious_metals": "Precious metals",
    "reits": "REITs",
    "cash": "Cash",
    "portfolio": "Portfolio",
    "us_ig": "US IG credit",
    "ig_model": "IG (Baa model)",
    "ig_fund": "IG fund",
    "hy_fund": "HY fund",
    "em_debt": "EM debt fund",
    "govt_fund": "Govt bond fund",
    "tips": "TIPS fund",
    "gsci": "GSCI fund",
    "tbills": "Cash (1m T-bills)",
}


def label(name: str) -> str:
    """Presentation label for a column name."""
    return DISPLAY_NAMES.get(str(name), str(name).replace("_", " "))


SURFACE = "#000000"
INK = "#f2f2f2"
INK_SECONDARY = "#bdbdbd"
INK_MUTED = "#8c8c8c"
GRID = "#262626"
SPINE = "#333333"
BASELINE = "#5a5a5a"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"

#: Width of the PNG fallback. Figures themselves carry no width: they fill the
#: column they are shown in (a VS Code cell, or an exported HTML page).
PNG_WIDTH = 1100

#: Figure margins in pixels; the right margin leaves room for end labels.
MARGIN = {"l": 70, "r": 120, "t": 55, "b": 55}


def use_house_style(*, png_scale: float = 2) -> None:
    """Register the terminal template and the interactive-plus-PNG renderer.

    ``plotly_mimetype+png`` puts two representations in every output: the
    Plotly JSON that Jupyter and VS Code render interactively, and a PNG that
    viewers without Plotly (GitHub, PDF export) fall back to.
    """
    axis = {
        "gridcolor": GRID,
        "linecolor": SPINE,
        "showline": True,
        "zeroline": False,
        "ticks": "outside",
        "tickcolor": SPINE,
        "ticklen": 4,
        "tickfont": {"color": INK_SECONDARY, "size": 11},
        "title": {"font": {"color": INK_SECONDARY, "size": 12}},
    }
    pio.templates["terminal"] = go.layout.Template(
        layout={
            "paper_bgcolor": SURFACE,
            "plot_bgcolor": SURFACE,
            "font": {"family": FONT, "color": INK_SECONDARY, "size": 12},
            "title": {"font": {"color": INK, "size": 16, "weight": "bold"}, "x": 0.01, "xanchor": "left"},
            "xaxis": axis,
            "yaxis": axis,
            "colorway": CATEGORICAL,
            "legend": {"bgcolor": "rgba(0,0,0,0)", "font": {"color": INK_SECONDARY, "size": 11}},
            "hoverlabel": {
                "bgcolor": "#111111",
                "bordercolor": AMBER,
                "font": {"family": FONT, "color": INK, "size": 12},
            },
            "margin": MARGIN,
        }
    )
    pio.templates.default = "terminal"
    pio.renderers.default = "plotly_mimetype+png"
    pio.renderers["png"].scale = png_scale
    pio.renderers["png"].width = PNG_WIDTH
    pio.renderers["plotly_mimetype"].config = {"responsive": True}


# --------------------------------------------------------------------------- #
# Figure plumbing
# --------------------------------------------------------------------------- #


def figure(*, title: str = "", width: int | None = None, height: int = 440) -> go.Figure:
    """A single-panel figure in the house template."""
    fig = go.Figure()
    fig.update_layout(title_text=title, width=width, height=height)
    return fig


def subplots(
    rows: int = 1,
    cols: int = 2,
    *,
    titles: tuple[str, ...] = (),
    width: int | None = None,
    height: int = 440,
    shared_y: bool = False,
    **kwargs,
) -> go.Figure:
    """A multi-panel figure; panel titles sit top-left, like the figure title."""
    fig = make_subplots(
        rows=rows, cols=cols, subplot_titles=titles, shared_yaxes=shared_y,
        horizontal_spacing=kwargs.pop("horizontal_spacing", 0.1), **kwargs,
    )
    for annotation in fig.layout.annotations:
        # make_subplots centres each panel title over its panel; move it left.
        annotation.update(
            x=annotation.x - _panel_half_width(fig, annotation), xanchor="left",
            font={"color": INK, "size": 14, "weight": "bold"},
        )
    fig.update_layout(width=width, height=height)
    return fig


def _panel_half_width(fig: go.Figure, annotation) -> float:
    """Half the width of the panel an auto-generated subplot title sits over."""
    for name in fig.layout:
        if name.startswith("xaxis"):
            start, end = fig.layout[name].domain
            if abs((start + end) / 2 - annotation.x) < 1e-6:
                return (end - start) / 2
    return 0.0


def _cell(fig: go.Figure | None, row: int | None, col: int | None, title: str, width: int | None, height: int):
    """Return (fig, subplot kwargs) — a new single figure, or one panel of ``fig``."""
    if fig is None:
        return figure(title=title, width=width, height=height), {}
    return fig, {"row": row or 1, "col": col or 1}


def _plot_height(fig: go.Figure, cell: dict) -> float:
    """Approximate pixel height of the panel ``cell`` refers to."""
    total = (fig.layout.height or 440) - MARGIN["t"] - MARGIN["b"]
    if not cell:
        return total
    start, end = fig.get_subplot(cell["row"], cell["col"]).yaxis.domain
    return total * (end - start)


def _x(index) -> pd.DatetimeIndex:
    return index.to_timestamp(how="end") if isinstance(index, pd.PeriodIndex) else index


def year_axis(fig: go.Figure, cell: dict | None = None, step: int = 5) -> None:
    """Tick a date axis every ``step`` years, labelled '70, '75, ...

    Two-digit years are unambiguous here: nothing in the study plots before 1970.
    """
    fig.update_xaxes(dtick=f"M{12 * step}", tick0="1970-01-01", tickformat="'%y", **(cell or {}))


def percent_axis(fig: go.Figure, decimals: int = 0, cell: dict | None = None, axis: str = "y") -> None:
    update = fig.update_yaxes if axis == "y" else fig.update_xaxes
    update(ticksuffix="%", tickformat=f".{decimals}f", **(cell or {}))


# --------------------------------------------------------------------------- #
# Time series
# --------------------------------------------------------------------------- #


def line_chart(
    frame: pd.DataFrame,
    *,
    fig: go.Figure | None = None,
    row: int | None = None,
    col: int | None = None,
    title: str = "",
    ylabel: str = "",
    label_ends: bool = True,
    colours: dict[str, str] | None = None,
    log: bool = False,
    percent: int | None = None,
    width: int | None = None,
    height: int = 440,
) -> go.Figure:
    """Multi-series line chart, identified by direct labels at each line's end.

    Labels take the series colour and replace the legend (terminal style); they
    are nudged apart vertically so series that finish close together stay
    legible. With ``label_ends=False`` a legend is drawn instead. ``percent``
    formats the y axis as a percentage with that many decimals.
    """
    fig, cell = _cell(fig, row, col, title, width, height)
    x = _x(frame.index)
    quarterly = isinstance(frame.index, pd.PeriodIndex) and frame.index.freqstr.startswith("Q")
    decimals = 2 if percent is None else percent + 1
    value_format = f"%{{y:.{decimals}f}}{'' if percent is None else '%'}"
    colour_of = {}
    for position, column in enumerate(frame.columns):
        colour = (colours or {}).get(column) or SERIES_COLOURS.get(
            str(column), CATEGORICAL[position % len(CATEGORICAL)]
        )
        colour_of[column] = colour
        fig.add_trace(
            go.Scatter(
                x=x, y=frame[column].values, name=label(column), mode="lines",
                line={"color": colour, "width": 2},
                showlegend=not label_ends and len(frame.columns) > 1,
                hovertemplate=f"{label(column)}: {value_format}<extra></extra>",
            ),
            **cell,
        )

    if log:
        fig.update_yaxes(type="log", dtick=1, **cell)  # label decades only: 1, 10, 100
    else:
        fig.add_hline(y=0, line={"color": BASELINE, "width": 1}, **cell)
    if percent is not None:
        percent_axis(fig, percent, cell)
    fig.update_yaxes(title_text=ylabel, **cell)
    fig.update_xaxes(
        hoverformat="%Y Q%q" if quarterly else "%b %Y",
        showspikes=True, spikemode="across", spikethickness=1, spikecolor=INK_MUTED, spikedash="dot",
        **cell,
    )
    span = x.max() - x.min()
    # Pin the range to the data (plus a sliver of room for the end labels), so
    # the 5-year ticks cannot drag the axis out past the last observation.
    fig.update_xaxes(range=[x.min() - span * 0.01, x.max() + span * 0.02], **cell)
    if span > pd.Timedelta(days=15 * 365):
        year_axis(fig, cell)
    fig.update_layout(hovermode="x unified")
    if label_ends:
        _label_line_ends(fig, cell, frame, x, colour_of, log=log)
    elif len(frame.columns) > 1:
        fig.update_layout(legend={"x": 0.01, "y": 0.99, "xanchor": "left", "yanchor": "top"})
    return fig


def _label_line_ends(fig, cell, frame, x, colour_of, *, log: bool, gap_px: float = 15) -> None:
    """Series-coloured labels at each line's last point, pushed apart if crowded."""
    values = frame.to_numpy(dtype=float)
    values = np.log10(values) if log else values
    low, high = np.nanmin(values), np.nanmax(values)
    px_per_unit = _plot_height(fig, cell) / ((high - low) * 1.1 or 1.0)

    ends = []
    for column in frame.columns:
        last = frame[column].last_valid_index()
        if last is None:
            continue
        y_last = float(frame[column].loc[last])
        position = (np.log10(y_last) if log else y_last) * px_per_unit
        ends.append((position, x[frame.index.get_loc(last)], y_last, column))

    ends.sort(key=lambda end: -end[0])
    placed: list[float] = []
    for position, *_ in ends:
        placed.append(min(position, placed[-1] - gap_px) if placed else position)
    for (position, x_last, y_last, column), target in zip(ends, placed, strict=True):
        fig.add_annotation(
            # On a log axis, annotation y is given in log10 units.
            x=x_last, y=np.log10(y_last) if log else y_last, text=label(column),
            showarrow=False, xanchor="left", xshift=6, yshift=target - position,
            font={"color": colour_of[column], "size": 12}, **cell,
        )
    if not cell and ends:
        # Labels sit in the right margin; widen it to fit the longest one (~7px
        # per character at size 12), since the plot no longer has a fixed width.
        longest = max(len(label(column)) for *_, column in ends)
        fig.update_layout(margin={"r": max(MARGIN["r"], 7 * longest + 16)})


def wealth_chart(returns: pd.DataFrame, *, start: str = "1972-01", **kwargs) -> go.Figure:
    """Cumulative total return on a log scale, indexed to 1 at ``start``."""
    wealth = (1.0 + returns).cumprod().loc[pd.Period(start, freq="M"):]
    wealth = wealth / wealth.iloc[0]
    wealth.index = pd.PeriodIndex(wealth.index, freq="M")
    kwargs.setdefault("ylabel", f"index, {start[:4]} = 1")
    return line_chart(wealth, log=True, **kwargs)


def shade_regimes(fig: go.Figure, classification: pd.Series, cell: dict | None = None, *, opacity: float = 0.3) -> None:
    """Tint the plot background by inflation regime, one block per run of quarters."""
    cell = cell or {}
    regimes = classification.dropna()
    runs = (regimes != regimes.shift()).cumsum()
    for _, block in regimes.groupby(runs):
        regime = block.iloc[0]
        if regime not in POLARITY or regime == "stable":
            continue
        fig.add_vrect(
            x0=block.index[0].to_timestamp(how="start"), x1=block.index[-1].to_timestamp(how="end"),
            fillcolor=POLARITY[regime], opacity=opacity, line_width=0, layer="below", **cell,
        )
    for regime in ("upside", "downside"):  # legend swatches for the shading
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None], mode="markers", name=f"{regime} surprise",
                marker={"symbol": "square", "size": 12, "color": POLARITY[regime], "opacity": 0.6},
                hoverinfo="skip",
            ),
            **cell,
        )


def regime_chart(series: pd.Series, classification: pd.Series, **kwargs) -> go.Figure:
    """A single series over a background shaded by inflation surprise regime."""
    fig = line_chart(series.to_frame(), label_ends=False, **kwargs)
    shade_regimes(fig, classification)
    fig.data[0].customdata = classification.reindex(series.index).fillna("—").values
    fig.data[0].hovertemplate = fig.data[0].hovertemplate.replace("<extra>", " · %{customdata} quarter<extra>")
    fig.update_layout(legend={"x": 0.99, "y": 0.99, "xanchor": "right", "yanchor": "top"})
    return fig


def shade_span(fig: go.Figure, start: str, end: str, *, freq: str = "Q", note: str = "") -> None:
    """Mute a stretch of the time axis, e.g. a spliced or estimated period."""
    fig.add_vrect(
        x0=pd.Period(start, freq=freq).to_timestamp(), x1=pd.Period(end, freq=freq).to_timestamp(how="end"),
        fillcolor=INK_MUTED, opacity=0.18, line_width=0, layer="below",
        annotation_text=note, annotation_position="top left",
        annotation_font={"color": INK_MUTED, "size": 11},
    )


# --------------------------------------------------------------------------- #
# Cross-sections
# --------------------------------------------------------------------------- #


def _grouped_bars(
    fig, cell, assets, groups, values_of, colour_of, *, text_format: str, hover_format: str, show_legend: bool
) -> None:
    for group in groups:
        values = [values_of(asset, group) for asset in assets]
        fig.add_trace(
            go.Bar(
                x=[label(a) for a in assets], y=values, name=group, marker_color=colour_of[group],
                legendgroup=group, showlegend=show_legend,
                text=[text_format.format(v) if pd.notna(v) else "" for v in values],
                textposition="outside", textfont={"color": INK_SECONDARY, "size": 10},
                cliponaxis=False,
                hovertemplate=f"%{{x}} · {group}: {hover_format}<extra></extra>",
            ),
            **cell,
        )
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08, hovermode="closest")
    fig.update_xaxes(showgrid=False, **cell)
    fig.add_hline(y=0, line={"color": BASELINE, "width": 1}, **cell)
    if show_legend:
        fig.update_layout(legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.12})


def sensitivity_bars(
    table: pd.DataFrame,
    *,
    factor: str,
    fig: go.Figure | None = None,
    row: int | None = None,
    col: int | None = None,
    title: str = "",
    order: list[str] | None = None,
    show_legend: bool = True,
    width: int | None = None,
    height: int = 440,
) -> go.Figure:
    """Grouped bars of change / surprise / combined sensitivity per asset.

    ``factor`` is ``"infl"`` or ``"growth"``; the table is the frame returned by
    ``metrics.sensitivity_table``. Every bar carries its value.
    """
    fig, cell = _cell(fig, row, col, title, width, height)
    _grouped_bars(
        fig, cell, order or list(table.index), ["change", "surprise", "combined"],
        lambda asset, leg: table.loc[asset, f"{factor}_{leg}"], LEG_COLOURS,
        text_format="{:+.2f}", hover_format="%{y:+.4r}", show_legend=show_legend,
    )
    fig.update_yaxes(title_text="correlation", **cell)
    return fig


def tritile_bars(
    averages: pd.DataFrame,
    *,
    fig: go.Figure | None = None,
    row: int | None = None,
    col: int | None = None,
    title: str = "",
    ylabel: str = "average quarterly return",
    width: int | None = None,
    height: int = 460,
) -> go.Figure:
    """Average return per asset in upside / stable / downside inflation quarters."""
    fig, cell = _cell(fig, row, col, title, width, height)
    regimes = [r for r in POLARITY_ORDER if r in averages.columns]
    _grouped_bars(
        fig, cell, list(averages.index), regimes, lambda asset, regime: averages.loc[asset, regime], POLARITY,
        text_format="{:+.1f}%", hover_format="%{y:+.4r}%", show_legend=True,
    )
    fig.update_yaxes(title_text=ylabel, **cell)
    percent_axis(fig, 0, cell)
    return fig


def upside_minus_downside(
    averages: pd.DataFrame,
    *,
    fig: go.Figure | None = None,
    row: int | None = None,
    col: int | None = None,
    title: str = "",
    width: int | None = None,
    height: int = 460,
) -> go.Figure:
    """The spread a single number can carry: upside-quarter return minus downside."""
    fig, cell = _cell(fig, row, col, title, width, height)
    spread = (averages["upside"] - averages["downside"]).sort_values()
    fig.add_trace(
        go.Bar(
            x=spread.values, y=[label(a) for a in spread.index], orientation="h",
            marker_color=[POLARITY["upside"] if v >= 0 else POLARITY["downside"] for v in spread],
            text=[f"{v:+.1f}%" for v in spread], textposition="outside", cliponaxis=False,
            textfont={"color": INK_SECONDARY, "size": 10}, showlegend=False,
            hovertemplate="%{y}: %{x:+.4r}pp per quarter<extra></extra>",
        ),
        **cell,
    )
    fig.add_vline(x=0, line={"color": BASELINE, "width": 1}, **cell)
    fig.update_yaxes(showgrid=False, ticksuffix="  ", **cell)
    percent_axis(fig, 0, cell, axis="x")
    # Headroom both sides so the outside value labels never touch the tick labels.
    reach = float(np.nanmax(np.abs(spread.values)))
    fig.update_xaxes(range=[min(spread.min(), 0) - 0.3 * reach, max(spread.max(), 0) + 0.3 * reach], **cell)
    return fig


def label_positions(x, y, span: float, *, near: float = 0.08) -> list[str]:
    """Text positions for point labels, cycling so crowded neighbours don't collide.

    A point within ``near`` × span of a point already placed takes the next
    position in the cycle; isolated points keep the first.
    """
    cycle = ["top right", "bottom right", "top left", "bottom left", "middle right"]
    placed: list[tuple[float, float]] = []
    out = []
    for point in zip(x, y):
        crowd = sum(abs(point[0] - p[0]) < span * near and abs(point[1] - p[1]) < span * near for p in placed)
        out.append(cycle[crowd % len(cycle)])
        placed.append(point)
    return out


def sensitivity_scatter(
    table: pd.DataFrame,
    *,
    fig: go.Figure | None = None,
    row: int | None = None,
    col: int | None = None,
    title: str = "Growth and inflation sensitivities",
    limit: float | None = None,
    width: int | None = None,
    height: int = 620,
) -> go.Figure:
    """Partial correlations to inflation (x) against growth (y).

    Every point is direct-labelled, so identity is carried by text and one hue
    suffices — which also sidesteps the all-pairs colour cap that a seven-way
    coloured scatter would breach.
    """
    fig, cell = _cell(fig, row, col, title, width, height)
    x = table["infl_partial"].astype(float)
    y = table["growth_partial"].astype(float)
    span = limit or float(np.nanmax(np.abs(np.concatenate([x.values, y.values]))) * 1.35)

    positions = label_positions(x.values, y.values, span)

    fig.add_hline(y=0, line={"color": BASELINE, "width": 1}, **cell)
    fig.add_vline(x=0, line={"color": BASELINE, "width": 1}, **cell)
    fig.add_trace(
        go.Scatter(
            x=x, y=y, mode="markers+text", text=[label(a) for a in table.index], textposition=positions,
            textfont={"color": INK_SECONDARY, "size": 11}, showlegend=False, cliponaxis=False,
            marker={"size": 11, "color": AMBER, "line": {"color": SURFACE, "width": 1.5}},
            hovertemplate="%{text}<br>inflation %{x:+.4r}<br>growth %{y:+.4r}<extra></extra>",
        ),
        **cell,
    )
    fig.update_xaxes(range=[-span, span], title_text="partial correlation to inflation metric", **cell)
    fig.update_yaxes(range=[-span, span], title_text="partial correlation to growth metric", **cell)
    fig.update_layout(hovermode="closest")
    if not cell:
        # Both axes share one range, so pin 1:1: the map stays square and centred
        # however wide the column it is shown in.
        fig.update_xaxes(constrain="domain")
        fig.update_yaxes(scaleanchor="x", scaleratio=1, constrain="domain")
        fig.update_layout(margin={**MARGIN, "r": 50})
    return fig


# --------------------------------------------------------------------------- #
# Time-varying correlations
# --------------------------------------------------------------------------- #

#: Sequential ramp for dates on black: dim early, bright recent (one hue, amber).
DATE_SCALE = [[0.0, "#4a2800"], [0.5, AMBER], [1.0, "#ffe0b2"]]


def correlation_scatter(
    returns: pd.DataFrame,
    metric: pd.Series,
    *,
    title: str = "Returns against the inflation metric, coloured by date",
    width: int | None = None,
    height: int = 560,
) -> go.Figure:
    """Year-on-year return against the inflation metric, one point per quarter.

    Points are coloured by date, so a sensitivity that drifted over time would
    show as colour clustering along the x axis. A dropdown switches asset; it is
    native Plotly, so it works in an exported page without a kernel.
    """
    fig = figure(title=title, width=width, height=height)
    assets = list(returns.columns)
    for position, asset in enumerate(assets):
        both = pd.concat([metric.rename("metric"), returns[asset].rename("ret")], axis=1).dropna()
        when = both.index.to_timestamp(how="end")
        years = when.year + (when.month - 1) / 12
        fig.add_trace(
            go.Scatter(
                x=both["metric"], y=both["ret"], mode="markers", name=label(asset),
                visible=position == 0, showlegend=False,
                customdata=np.array([f"{p.year} Q{p.quarter}" for p in both.index]),
                marker={
                    "size": 8, "color": years, "colorscale": DATE_SCALE, "cmin": 1972, "cmax": years.max(),
                    "line": {"color": SURFACE, "width": 0.5},
                    "colorbar": {"title": {"text": "date", "font": {"color": INK_SECONDARY}},
                                 "tickfont": {"color": INK_SECONDARY}, "thickness": 12, "outlinewidth": 0},
                },
                hovertemplate=(f"{label(asset)} · %{{customdata}}<br>inflation metric %{{x:.3r}}pp"
                               "<br>YoY return %{y:.3r}%<extra></extra>"),
            )
        )
    fig.update_layout(
        updatemenus=[{
            "buttons": [
                {"label": label(asset), "method": "update",
                 "args": [{"visible": [a == asset for a in assets]}, {"yaxis.autorange": True}]}
                for asset in assets
            ],
            "x": 1.0, "xanchor": "right", "y": 1.13, "yanchor": "top",
            "bgcolor": "#111111", "bordercolor": SPINE, "font": {"color": INK_SECONDARY},
            "active": 0,
        }],
        hovermode="closest",
    )
    fig.add_hline(y=0, line={"color": BASELINE, "width": 1})
    fig.add_vline(x=0, line={"color": BASELINE, "width": 1})
    fig.update_xaxes(title_text="inflation metric (pp)")
    fig.update_yaxes(title_text="year-on-year return", ticksuffix="%")
    return fig


def rolling_correlation(
    returns: pd.DataFrame,
    metric: pd.Series,
    *,
    window: int = 40,
    shown: list[str] | None = None,
    title: str = "",
    width: int | None = None,
    height: int = 460,
) -> go.Figure:
    """Rolling correlation of each asset's YoY return with the inflation metric.

    ``window`` is in quarters (40 = ten years). Series outside ``shown`` start
    hidden; click them in the legend to add them.
    """
    rolling = pd.DataFrame(
        {asset: returns[asset].rolling(window, min_periods=window).corr(metric) for asset in returns.columns}
    ).dropna(how="all")
    fig = line_chart(
        rolling, title=title or f"Rolling {window // 4}-year correlation with the inflation metric",
        ylabel="correlation", label_ends=False, width=width, height=height,
    )
    for trace, asset in zip(fig.data, rolling.columns, strict=True):
        trace.hovertemplate = f"{label(asset)}: %{{y:+.3r}}<extra></extra>"
        if shown is not None and asset not in shown:
            trace.visible = "legendonly"
    fig.update_yaxes(range=[-1, 1], dtick=0.5)
    fig.update_layout(legend={"x": 1.01, "y": 1, "xanchor": "left", "yanchor": "top"}, margin={**MARGIN, "r": 170})
    return fig
