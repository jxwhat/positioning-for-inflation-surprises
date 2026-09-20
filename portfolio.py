"""The backtesting app: an "all weather" portfolio against the macro map.

``backtest_figure`` draws the exhibit for one fixed weight vector and horizon.
It renders in a static export, in a PDF, or anywhere else, and it is the
function a web front end mirrors.

🚨 **There is deliberately no live widget here any more (user, 2026-09-20).**
There used to be: ``interactive_panel``, an ipywidgets panel with a horizon
selector and one slider per sleeve. It was retired because maintaining a
second interactive surface meant keeping two of everything and re-testing a
Plotly-in-VS-Code rendering path (blank table headers on a widget with no
fixed width) that only the notebook ever hit. The notebook is static; the app
is interactive.

The universe is wider than the study's: it adds the backtest-only sleeves from
``dataset.backtest_universe`` (modelled IG, credit and government funds, TIPS,
a GSCI fund). Not every sleeve exists for every horizon, so each horizon offers
only the sleeves with continuous history from its start date.

Rebalancing is monthly: the weights are applied to monthly total returns, which
is equivalent to trading back to target at each month end, ignoring costs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import charts
import dataset
import metrics

#: Illustrative weights: 25/50/5/20.
#:
#: Chosen 2026-09-20 (user request) to sit close to ZERO on BOTH axes, which
#: the previous 60/25/10/15 did not: that blend was inflation-neutral
#: (−0.01) but carried a moderate growth exposure (+0.32), so it demonstrated
#: half of the study's point and left the reader to imagine the other half.
#: This one runs inflation −0.019, growth +0.014 on the full sample — both
#: inside the noise of the estimate.
#:
#: Picked by grid-searching 8,926 five-sleeve allocations in 5% steps and
#: taking the best worst-case |partial| among the ones that stay investable.
#: A slightly more neutral combination exists (10/60/20/5/5, both ≈0.00) and
#: was rejected: with a 10% equity sleeve it is a bond portfolio, and it reads
#: oddly as the default for something called an all-weather demo.
#:
#: 🚨 STATIC, by design. These are not re-optimised as data arrives — the
#: study is explicit that everything here is chosen in-sample, and a default
#: that silently re-fitted itself each month would make that worse while
#: looking like it had made it better. They sum to 1.00, so normalising is a
#: no-op until the reader moves a slider.
EXAMPLE_WEIGHTS = {"equities": 0.25, "ust_10y": 0.50, "commodities": 0.05, "gold": 0.20}

#: Comparison lines on the wealth chart and columns in the statistics table.
BENCHMARKS = ["equities", "ust_10y", "sixty_forty"]

#: Backtest horizons. Each start is where more sleeves become available:
#: 1986 brings the credit and government funds, 2007 every remaining sleeve.
HORIZONS = {
    "Full sample (1972–)": "1972-01",
    "Since 1986": "1986-01",
    "Since 2007": "2007-01",
}

#: Slider layout: sleeves grouped by asset class, in display order.
SLEEVE_GROUPS = {
    "Equities": ["equities"],
    "Rates": ["ust_5y", "ust_10y", "ust_20y", "govt_fund", "tips"],
    "Credit": ["ig_model", "ig_fund", "hy_fund", "em_debt"],
    "Real assets": ["commodities", "gsci", "gold", "precious_metals", "reits"],
    "Cash": ["tbills"],
}


def blend(
    weights: dict[str, float],
    monthly_returns: pd.DataFrame,
    *,
    normalise: bool = True,
    start: pd.Period | str | None = "1972-01",
) -> pd.Series:
    """Monthly rebalanced portfolio return from a weight vector.

    ``start`` defaults to the study window rather than to the longest common
    history of the sleeves. Left unbounded, gold's 1968 start would pull the
    portfolio's statistics back four years before the period every sensitivity
    in this notebook is measured over.
    """
    used = {k: v for k, v in weights.items() if v}
    total = sum(used.values())
    if normalise and total:
        used = {k: v / total for k, v in used.items()}
    sleeves = monthly_returns[list(used)].dropna()
    if start is not None:
        sleeves = sleeves.loc[pd.Period(start, freq="M"):]
    return sleeves.mul(pd.Series(used)).sum(axis=1).rename("portfolio")


def summary_statistics(monthly_returns: pd.Series, cash: pd.Series | None = None) -> dict:
    """The usual backtest statistics for a monthly total-return series.

    Sharpe and Sortino are computed on returns in excess of ``cash`` — the
    one-month T-bill return, month by month — so the risk-free rate is the one
    actually available over the backtest, not a fixed assumption. Without
    ``cash`` they fall back to raw returns.
    """
    clean = monthly_returns.dropna()
    if clean.empty:
        return {}
    rf = cash.reindex(clean.index).fillna(0.0) if cash is not None else pd.Series(0.0, index=clean.index)
    excess = clean - rf
    root12 = np.sqrt(12.0)

    # Wealth from a starting value of 1, so a first-month loss counts as drawdown.
    wealth = pd.concat([pd.Series([1.0]), (1.0 + clean).cumprod().reset_index(drop=True)], ignore_index=True)
    drawdown = wealth / wealth.cummax() - 1.0
    # Worst peak-to-trough inside any 12-month window (13 wealth points: start + 12 months).
    drawdown_12m = (wealth / wealth.rolling(13, min_periods=1).max() - 1.0).min()
    rolling_12m = (1.0 + clean).rolling(12).apply(np.prod, raw=True) - 1.0
    underwater = drawdown < 0
    longest = int(underwater.groupby((~underwater).cumsum()).sum().max())

    years = len(clean) / 12.0
    annualised = wealth.iloc[-1] ** (1.0 / years) - 1.0
    volatility = clean.std() * root12
    downside = np.sqrt((excess.clip(upper=0.0) ** 2).mean()) * root12
    max_drawdown = float(drawdown.min())
    return {
        "annualised_return": float(annualised),
        "volatility": float(volatility),
        "sharpe": float(excess.mean() * 12 / (excess.std() * root12)) if excess.std() else np.nan,
        "sortino": float(excess.mean() * 12 / downside) if downside else np.nan,
        "max_drawdown": max_drawdown,
        "max_drawdown_12m": float(drawdown_12m),
        "worst_12m": float(rolling_12m.min()),
        "best_12m": float(rolling_12m.max()),
        "longest_drawdown_months": longest,
        "calmar": float(annualised / abs(max_drawdown)) if max_drawdown else np.nan,
        "positive_months": float((clean > 0).mean()),
        "cash_return": float((1.0 + rf).prod() ** (1.0 / years) - 1.0),
        "start": clean.index.min(),
        "end": clean.index.max(),
        "months": len(clean),
    }


#: Rows of the statistics table: (label, key, format).
STAT_ROWS = [
    ("Annualised return", "annualised_return", "{:.2%}"),
    ("Annualised volatility", "volatility", "{:.2%}"),
    ("Sharpe ratio (vs T-bills)", "sharpe", "{:.2f}"),
    ("Sortino ratio (vs T-bills)", "sortino", "{:.2f}"),
    ("Max drawdown", "max_drawdown", "{:.1%}"),
    ("Max 12-month drawdown", "max_drawdown_12m", "{:.1%}"),
    ("Worst 12-month return", "worst_12m", "{:.1%}"),
    ("Best 12-month return", "best_12m", "{:.1%}"),
    ("Longest drawdown (months)", "longest_drawdown_months", "{:d}"),
    ("Calmar ratio", "calmar", "{:.2f}"),
    ("Positive months", "positive_months", "{:.0%}"),
    ("Inflation partial correlation", "infl_partial", "{:+.2f}"),
    ("Growth partial correlation", "growth_partial", "{:+.2f}"),
]


def sensitivity_row(
    portfolio_monthly: pd.Series,
    inflation: pd.DataFrame,
    growth: pd.DataFrame,
) -> pd.DataFrame:
    """Sensitivity table for a single portfolio, shaped like the asset table."""
    yoy = dataset.quarterly_yoy_returns(portfolio_monthly.to_frame())
    return metrics.sensitivity_table(yoy, inflation, growth)


# --------------------------------------------------------------------------- #
# Horizons and availability
# --------------------------------------------------------------------------- #


def available_sleeves(universe: pd.DataFrame, start: str) -> list[str]:
    """Sleeves with continuous history from ``start`` to their last observation.

    A sleeve that starts late, or has a hole after ``start`` (the 20-year
    treasury's 1987-93 gap), is excluded rather than silently shortening the
    backtest.
    """
    first = pd.Period(start, freq="M")
    out = []
    for group in SLEEVE_GROUPS.values():
        for sleeve in group:
            if sleeve not in universe:
                continue
            series = universe[sleeve]
            valid = series.first_valid_index()
            if valid is None or valid > first:
                continue
            if series.loc[first : series.last_valid_index()].isna().any():
                continue
            out.append(sleeve)
    return out


def first_available(universe: pd.DataFrame, sleeve: str) -> str:
    """When a sleeve becomes usable, for the 'unavailable' note in the widget."""
    series = universe[sleeve]
    history = series.loc[series.first_valid_index() : series.last_valid_index()]
    holes = history.index[history.isna()]
    return str(holes.max() + 1 if len(holes) else history.index.min())


def horizon_tables(universe: pd.DataFrame, inflation: pd.DataFrame, growth: pd.DataFrame) -> dict:
    """Asset sensitivities for every horizon, computed once up front.

    Each table holds the sleeves available at that horizon plus the 60/40
    benchmark (which has no slider but appears on the map and in the table).
    """
    yoy = dataset.quarterly_yoy_returns(universe)
    tables = {}
    for name, start in HORIZONS.items():
        sleeves = available_sleeves(universe, start) + ["sixty_forty"]
        window = yoy.loc[pd.Period(start, freq="M").asfreq("Q"):, sleeves]
        tables[name] = metrics.sensitivity_table(window, inflation, growth)
    return tables


# --------------------------------------------------------------------------- #
# The figure
# --------------------------------------------------------------------------- #


def _caption(weights: dict, stats: dict, normalise: bool, horizon: str) -> str:
    gross = sum(v for v in weights.values() if v)
    sleeves = "  ".join(f"{charts.label(k)} {v:.0%}" for k, v in weights.items() if v) or "no sleeves selected"
    period = f"   |   {stats['start']} to {stats['end']}" if stats else ""
    return f"{horizon}   |   {sleeves}   |   gross {gross:.0%}{' (normalised)' if normalise else ''}{period}"


def _cell(stats: dict, key: str, fmt: str) -> str:
    """One formatted statistic, or an en dash where it is missing."""
    value = stats.get(key)
    return "–" if value is None or (isinstance(value, float) and np.isnan(value)) else fmt.format(value)


def _statistics_table(columns: dict[str, dict]) -> go.Table:
    """The comparison table: one column per series, rows from ``STAT_ROWS``."""
    names = list(columns)
    colours = [charts.INK] + [charts.SERIES_COLOURS.get(n, charts.INK) for n in names]
    return go.Table(
        columnwidth=[2.4] + [1] * len(names),
        header={
            "values": [""] + [f"<b>{charts.label(n)}</b>" for n in names],
            "fill_color": "#111111", "line_color": charts.SPINE, "height": 28,
            "font": {"color": colours, "size": 12, "family": charts.FONT},
            "align": ["left"] + ["right"] * len(names),
        },
        cells={
            "values": [[label for label, _, _ in STAT_ROWS]]
            + [[_cell(columns[n], key, fmt) for _, key, fmt in STAT_ROWS] for n in names],
            "fill_color": charts.SURFACE, "line_color": charts.GRID, "height": 23,
            "font": {"color": [charts.INK_SECONDARY] + [charts.INK] * len(names), "size": 12, "family": charts.FONT},
            "align": ["left"] + ["right"] * len(names),
        },
    )


STATISTICS_TITLE = "Backtest statistics (same months for every column)"


def backtest_figure(
    weights: dict[str, float],
    universe: pd.DataFrame,
    inflation: pd.DataFrame,
    growth: pd.DataFrame,
    *,
    horizon: str = "Full sample (1972–)",
    normalise: bool = True,
    tables: dict | None = None,
    with_table: bool = True,
):
    """The backtest exhibit: macro map, wealth against benchmarks, drawdown, statistics.

    Left, every sleeve available at this horizon as a faint dot, with the
    portfolio as the large white one. Right, cumulative return (log scale)
    against US equities, the 10-year Treasury and the 60/40 over the same
    months, above the portfolio's drawdown. Below, the statistics table for all
    four. The trace count is fixed so a live widget can update it in place.
    Returns ``(figure, stats, portfolio_table)``; ``portfolio_table.attrs["columns"]``
    holds the statistics per column. ``with_table=False`` leaves the table out
    of the figure, for callers that draw it as HTML (see ``statistics_html``).
    """
    start = HORIZONS[horizon]
    assets = (tables or horizon_tables(universe, inflation, growth))[horizon]
    usable = {k: v for k, v in weights.items() if v and k in assets.index and k != "sixty_forty"}
    returns = blend(usable, universe, normalise=normalise, start=start) if usable else pd.Series(dtype=float)
    cash = universe["tbills"].fillna(universe["cash"]) if "tbills" in universe else universe.get("cash")
    stats = summary_statistics(returns, cash)
    if len(returns) > 24:
        table = sensitivity_row(returns, inflation, growth)
        table.index = ["portfolio"]
    else:
        table = pd.DataFrame({"infl_partial": [np.nan], "growth_partial": [np.nan]}, index=["portfolio"])

    # Benchmarks over exactly the portfolio's months, so every column is comparable.
    months = returns.index
    benchmark_returns = {b: universe[b].reindex(months) for b in BENCHMARKS}
    columns = {"portfolio": {**stats, **table.loc["portfolio"].to_dict()}}
    for b, series in benchmark_returns.items():
        columns[b] = {**summary_statistics(series, cash), **assets.loc[b].to_dict()} if b in assets.index else {}

    table.attrs["columns"] = columns

    titles = ("Macro map (partial correlations)", "Cumulative total return (log scale)", "Drawdown from peak")
    if with_table:
        fig = charts.subplots(
            rows=3, cols=2, titles=(*titles, ""),
            specs=[[{"rowspan": 2}, {}], [None, {}], [{"type": "table", "colspan": 2}, None]],
            column_widths=[0.42, 0.58], row_heights=[0.38, 0.19, 0.43],
            horizontal_spacing=0.1, vertical_spacing=0.1, height=1120,
        )
    else:
        fig = charts.subplots(
            rows=2, cols=2, titles=titles, specs=[[{"rowspan": 2}, {}], [None, {}]],
            column_widths=[0.42, 0.58], row_heights=[0.67, 0.33],
            horizontal_spacing=0.1, vertical_spacing=0.1, height=680,
        )
    span = 0.8
    fig.add_hline(y=0, line={"color": charts.BASELINE, "width": 1}, row=1, col=1)
    fig.add_vline(x=0, line={"color": charts.BASELINE, "width": 1}, row=1, col=1)
    fig.add_trace(
        go.Scatter(
            x=assets["infl_partial"], y=assets["growth_partial"], mode="markers+text",
            text=[charts.label(a) for a in assets.index],
            textposition=charts.label_positions(assets["infl_partial"].values, assets["growth_partial"].values, span),
            textfont={"color": charts.INK_MUTED, "size": 10}, cliponaxis=False, showlegend=False,
            marker={"size": 8, "color": charts.INK_MUTED, "opacity": 0.7},
            hovertemplate="%{text}<br>inflation %{x:+.4r}<br>growth %{y:+.4r}<extra></extra>",
        ),
        row=1, col=1,
    )
    portfolio_colour = charts.SERIES_COLOURS["portfolio"]
    fig.add_trace(
        go.Scatter(
            x=table["infl_partial"], y=table["growth_partial"], mode="markers+text", text=["Portfolio"],
            textposition="bottom center", textfont={"color": portfolio_colour, "size": 12}, showlegend=False,
            marker={"size": 16, "color": portfolio_colour, "line": {"color": charts.SURFACE, "width": 2}},
            hovertemplate="Portfolio<br>inflation %{x:+.4r}<br>growth %{y:+.4r}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.update_xaxes(range=[-span, span], title_text="partial correlation to inflation metric", row=1, col=1)
    fig.update_yaxes(range=[-span, span], title_text="partial correlation to growth metric", row=1, col=1)

    x = months.to_timestamp(how="end") if len(months) else []
    for b, series in benchmark_returns.items():
        growth_of_1 = (1.0 + series.fillna(0.0)).cumprod().where(series.notna())
        fig.add_trace(
            go.Scatter(
                x=x, y=growth_of_1.values, mode="lines", name=charts.label(b),
                line={"color": charts.SERIES_COLOURS[b], "width": 1.3}, opacity=0.85,
                hovertemplate=f"{charts.label(b)}: %{{y:.4r}}×<extra></extra>",
            ),
            row=1, col=2,
        )
    wealth = (1.0 + returns).cumprod()
    drawdown = (wealth / wealth.cummax() - 1.0) * 100.0
    fig.add_trace(
        go.Scatter(
            x=x, y=wealth.values, mode="lines", name="Portfolio", line={"color": portfolio_colour, "width": 2.6},
            hovertemplate="Portfolio: %{y:.4r}×<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=drawdown.values, mode="lines", fill="tozeroy", showlegend=False,
            line={"color": charts.RED, "width": 1}, fillcolor="rgba(255, 82, 82, 0.35)",
            hovertemplate="%{x|%b %Y}: %{y:.3r}% from peak<extra></extra>",
        ),
        row=2, col=2,
    )
    if with_table:
        fig.add_trace(_statistics_table(columns), row=3, col=1)

    # Decade ticks once the curves span a decade; 1-2-5 ticks below that.
    curves = [trace.y for trace in fig.data[2:6] if trace.y is not None and len(trace.y)]
    values = np.concatenate([np.asarray(c, dtype=float) for c in curves]) if curves else np.array([1.0])
    low, high = (np.nanmin(values), np.nanmax(values)) if curves else (1.0, 1.0)
    decade_marks = [10.0**k for k in range(-2, 5) if low <= 10.0**k <= high]
    if len(decade_marks) >= 2:
        ticks = {"tickmode": "linear", "dtick": 1, "tickvals": None, "ticktext": None}
    else:  # fewer than two powers of ten in view: label a 1-2-5 sequence instead
        marks = [m * 10.0**k for k in range(-1, 3) for m in (1, 2, 5) if low * 0.9 <= m * 10.0**k <= high * 1.1]
        ticks = {"tickmode": "array", "dtick": None, "tickvals": marks, "ticktext": [f"{m:g}" for m in marks]}
    fig.update_yaxes(type="log", title_text="growth of 1", **ticks, row=1, col=2)
    fig.update_yaxes(ticksuffix="%", title_text="", row=2, col=2)
    for row in (1, 2):
        fig.update_xaxes(dtick="M60", tick0="1970-01-01", tickformat="'%y", row=row, col=2)
    fig.update_xaxes(showticklabels=False, row=1, col=2)
    wealth_x = fig.get_subplot(1, 2).xaxis.domain
    wealth_y = fig.get_subplot(1, 2).yaxis.domain
    if with_table:
        table_domain = fig.data[-1].domain
        fig.add_annotation(
            text=STATISTICS_TITLE, x=table_domain.x[0], y=table_domain.y[1],
            xref="paper", yref="paper", xanchor="left", yanchor="bottom", yshift=6, showarrow=False,
            font={"color": charts.INK, "size": 14, "weight": "bold"},
        )
    fig.update_layout(
        title={"text": _caption(weights, stats, normalise, horizon),
               "font": {"size": 12, "color": charts.INK_SECONDARY, "weight": "normal"}},
        margin={**charts.MARGIN, "t": 80, "r": 40}, hovermode="closest",
        legend={"x": wealth_x[0] + 0.01, "y": wealth_y[1] - 0.01, "xanchor": "left", "yanchor": "top",
                "bgcolor": "rgba(0,0,0,0.6)", "orientation": "h"},
    )
    return fig, stats, table


# Kept under its old name for any caller of the fixed-weight panel.
