"""Shock episodes: what the portfolio did while the macro was actually going wrong.

The rest of the study answers "how does this asset co-move with inflation
surprises, on average, across fifty years". That is the right question for
building the thing, and the wrong one for persuading anybody to hold it. A
reader who measures portfolios by total return looks at an all-weather sleeve
next to US equities, sees it lose over the full sample, and stops reading —
because the full sample is dominated by the decades in which nothing went
wrong, which are exactly the decades this portfolio is not for.

So this module asks the other question: **in the specific windows when
inflation surprised to the upside, or growth surprised to the downside, what
did each portfolio actually lose?** That is where a diversified sleeve earns
its keep, and it is invisible in a full-sample statistic.

**Episodes are derived, not chosen.** They are contiguous runs of quarters that
the study's own ``metrics.classify`` already calls a shock — the same z-score
tritile sort, at the same threshold, that every other exhibit uses. Nobody
picks the windows, they extend themselves as new data arrives, and there is no
opportunity to flatter the portfolio by choosing which crises to show.

🚨 **This is ex-post, in-sample, and not a trading rule.** The z-score is
computed over the full sample (as ``metrics.classify`` documents), so an
episode is only knowable after the fact, and its boundaries shift slightly as
the sample grows. Read it as "here is what happened in the bad windows", never
as "here is what a strategy would have earned" — nobody could have known in
1973 Q2 that the next six quarters were an episode.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import metrics

#: A single quarter over the line is noise; an episode has to persist.
#:
#: Two quarters is the shortest run that can be called an episode at all given
#: the metric's own construction: it is an overlapping year-on-year measure, so
#: consecutive quarters share three of their four months and a one-quarter
#: excursion is frequently one month's print.
MIN_QUARTERS = 2

#: Which tail of each metric is the bad one.
SHOCK_DIRECTION = {"inflation": "upside", "growth": "downside"}

#: How each is described where the label has to stand alone.
SHOCK_TITLE = {
    "inflation": "Inflation surprising to the upside",
    "growth": "Growth surprising to the downside",
}


@dataclass(frozen=True)
class Episode:
    """One contiguous run of shock quarters."""

    kind: str  # "inflation" | "growth"
    start: pd.Period  # quarterly
    end: pd.Period  # quarterly, inclusive
    #: Most extreme z-score reached inside the run, signed as the metric is.
    peak: float

    @property
    def label(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}–{self.end}"

    @property
    def quarters(self) -> int:
        return (self.end - self.start).n + 1

    @property
    def first_month(self) -> pd.Period:
        return self.start.asfreq("M", how="start")

    @property
    def last_month(self) -> pd.Period:
        return self.end.asfreq("M", how="end")


def find_episodes(
    combined: pd.Series,
    kind: str,
    *,
    threshold: float = 1.0,
    min_quarters: int = MIN_QUARTERS,
) -> list[Episode]:
    """Contiguous runs of shock quarters in one metric's combined series.

    ``combined`` is the ``combined`` column of a :func:`metrics.combine` frame.
    Classification is delegated to :func:`metrics.classify` rather than
    reimplemented, so this cannot drift from the map, the tables or the
    notebook's own sorting.
    """
    direction = SHOCK_DIRECTION[kind]
    z = metrics.zscore(combined)
    labels = metrics.classify(combined, threshold)
    hits = labels[labels == direction].index

    episodes: list[Episode] = []
    run: list[pd.Period] = []
    for quarter in hits:
        # A gap in the index is a gap in the episode: quarters are only
        # contiguous if they are literally adjacent.
        if run and quarter != run[-1] + 1:
            episodes.append(_build(kind, run, z))
            run = []
        run.append(quarter)
    if run:
        episodes.append(_build(kind, run, z))

    return [e for e in episodes if e.quarters >= min_quarters]


def _build(kind: str, run: list[pd.Period], z: pd.Series) -> Episode:
    values = z.loc[run]
    peak = values.max() if SHOCK_DIRECTION[kind] == "upside" else values.min()
    return Episode(kind=kind, start=run[0], end=run[-1], peak=float(peak))


def all_episodes(
    inflation: pd.DataFrame,
    growth: pd.DataFrame,
    *,
    threshold: float = 1.0,
    min_quarters: int = MIN_QUARTERS,
) -> list[Episode]:
    """Every inflation and growth episode, inflation first, each in date order."""
    return [
        *find_episodes(inflation["combined"].dropna(), "inflation", threshold=threshold, min_quarters=min_quarters),
        *find_episodes(growth["combined"].dropna(), "growth", threshold=threshold, min_quarters=min_quarters),
    ]


def window(monthly_returns: pd.Series, episode: Episode) -> pd.Series:
    """The months of ``monthly_returns`` that fall inside an episode."""
    return monthly_returns.loc[episode.first_month : episode.last_month].dropna()


def performance(monthly_returns: pd.Series, episode: Episode) -> dict:
    """What one return series did during one episode.

    ``total_return`` compounds the episode's months. ``max_drawdown`` is
    measured from a peak of 1.0 at the episode's start, NOT from a peak carried
    in from before it — the question is what this window cost, and inheriting a
    prior high would attribute an earlier decline to it.

    Returns empty-valued fields where the series does not cover the window at
    all, which is normal: most sleeves postdate 1973.
    """
    months = window(monthly_returns, episode)
    if months.empty:
        return {"total_return": np.nan, "max_drawdown": np.nan, "months": 0, "covered": False}

    # Wealth starts at 1.0 BEFORE the first month, exactly as
    # `portfolio.summary_statistics` does it. Without the leading 1.0 the
    # running peak begins at the first month's close, so a fall in the
    # episode's opening month is measured from a level the portfolio never
    # held and comes out too small.
    wealth = pd.concat([pd.Series([1.0]), (1.0 + months).cumprod().reset_index(drop=True)], ignore_index=True)
    drawdown = wealth / wealth.cummax() - 1.0
    return {
        "total_return": float(wealth.iloc[-1] - 1.0),
        "max_drawdown": float(drawdown.min()),
        "months": int(len(months)),
        # Partial coverage is still reported, but flagged: a sleeve that only
        # exists for the last four months of a six-quarter episode did not
        # live through that episode, and its drawdown is not comparable.
        "covered": bool(months.index[0] <= episode.first_month),
    }


def episode_table(series_by_name: dict[str, pd.Series], episodes: list[Episode]) -> pd.DataFrame:
    """One row per (episode, series): the shape the figure and the HTML read.

    Columns: kind, episode, quarters, peak, series, total_return,
    max_drawdown, months, covered.
    """
    rows = []
    for episode in episodes:
        for name, series in series_by_name.items():
            rows.append(
                {
                    "kind": episode.kind,
                    "episode": episode.label,
                    "quarters": episode.quarters,
                    "peak": episode.peak,
                    "series": name,
                    # Context only, and never grouped on: the summary below
                    # aggregates by kind and series, not by name.
                    "historical": "; ".join(historical_overlaps(episode)),
                    **performance(series, episode),
                }
            )
    return pd.DataFrame(rows)


def summarise(table: pd.DataFrame) -> pd.DataFrame:
    """Average and worst outcome per (kind, series), over fully covered episodes.

    🚨 Partially covered episodes are EXCLUDED, not averaged in. A sleeve that
    began midway through the 1973 episode would otherwise post a flattering
    drawdown for a window it mostly missed, and the comparison against equities
    — which cover every episode — would be against different periods.
    """
    covered = table[table["covered"] & table["months"].gt(0)]
    if covered.empty:
        return pd.DataFrame(columns=["kind", "series", "episodes", "mean_return", "worst_return", "mean_drawdown", "worst_drawdown"])
    grouped = covered.groupby(["kind", "series"], sort=False)
    return pd.DataFrame(
        {
            "episodes": grouped["episode"].nunique(),
            "mean_return": grouped["total_return"].mean(),
            "worst_return": grouped["total_return"].min(),
            "mean_drawdown": grouped["max_drawdown"].mean(),
            "worst_drawdown": grouped["max_drawdown"].min(),
        }
    ).reset_index()


# --------------------------------------------------------------------------- #
# Exhibits
# --------------------------------------------------------------------------- #


def episode_figure(
    table: pd.DataFrame,
    *,
    order: list[str] | None = None,
    height: int = 760,
    width: int | None = None,
):
    """Grouped bars: what each series returned, and lost, in every episode.

    Two columns (inflation shocks, growth shocks) by two rows (total return
    over the episode, worst drawdown inside it). Drawdown is the row that
    matters — it is the one a total-return reader has never been shown, and
    the one where a diversified sleeve wins.
    """
    import charts
    import plotly.graph_objects as go

    names = order or list(dict.fromkeys(table["series"]))
    kinds = [k for k in ("inflation", "growth") if (table["kind"] == k).any()]
    if not kinds:
        return charts.figure(title="No shock episodes in this sample", height=200)

    fig = charts.subplots(
        rows=2, cols=len(kinds), height=height, width=width,
        horizontal_spacing=0.09, vertical_spacing=0.13,
        titles=tuple(
            f"{SHOCK_TITLE[kind]} — {row}"
            for row in ("total return over the episode", "worst drawdown inside it")
            for kind in kinds
        ),
    )
    for column, kind in enumerate(kinds, start=1):
        sub = table[table["kind"] == kind]
        labels = list(dict.fromkeys(sub["episode"]))
        for row, field, fmt in ((1, "total_return", "{:+.0%}"), (2, "max_drawdown", "{:.0%}")):
            for name in names:
                series = sub[sub["series"] == name].set_index("episode")
                values = [
                    series.loc[e, field] * 100 if e in series.index and series.loc[e, "covered"] else np.nan
                    for e in labels
                ]
                fig.add_trace(
                    go.Bar(
                        x=labels, y=values, name=charts.label(name),
                        marker_color=charts.SERIES_COLOURS.get(name, charts.INK),
                        legendgroup=name, showlegend=(row == 1 and column == 1),
                        text=[fmt.format(v / 100) if pd.notna(v) else "" for v in values],
                        textposition="outside", textfont={"color": charts.INK_SECONDARY, "size": 9},
                        cliponaxis=False,
                        hovertemplate=f"%{{x}} · {charts.label(name)}: %{{y:.3r}}%<extra></extra>",
                    ),
                    row=row, col=column,
                )
            fig.update_yaxes(ticksuffix="%", row=row, col=column)
            fig.add_hline(y=0, line={"color": charts.BASELINE, "width": 1}, row=row, col=column)
            fig.update_xaxes(showgrid=False, row=row, col=column)

    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.06, hovermode="closest",
        legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.08},
    )
    return fig


# --------------------------------------------------------------------------- #
# Named historical episodes — background, not an input
# --------------------------------------------------------------------------- #

#: Recognisable macro episodes, for context beside the derived windows
#: (user, 2026-09-20: "more as annotation and background").
#:
#: 🚨 These are NOT what the study measures. Nothing here feeds a regression,
#: a classification or a backtest — the episodes the analysis uses are derived
#: from the metric by :func:`find_episodes`, precisely so that no one hand-picks
#: the windows. This list exists so a reader can see which recognisable event a
#: derived window corresponds to, and it is hand-dated from the conventional
#: chronology (NBER for the US recessions, the standard dating for the oil
#: shocks and the policy episodes).
#:
#: Dates are inclusive quarters. Where a conventional date is contested the
#: wider reading is taken, since the purpose is orientation rather than
#: precision — an episode that is a quarter long in one telling and two in
#: another is the same episode either way.
HISTORICAL_EPISODES: list[dict] = [
    {"name": "First oil shock (OPEC embargo)", "kind": "inflation", "start": "1973Q4", "end": "1974Q4",
     "note": "The October 1973 embargo roughly quadrupled the crude price. Inflation and recession arrived together, which is what made it the canonical stagflation."},
    {"name": "1973–75 recession", "kind": "growth", "start": "1973Q4", "end": "1975Q1",
     "note": "NBER peak November 1973 to trough March 1975. The deepest post-war contraction until 2008."},
    {"name": "Second oil shock (Iranian revolution)", "kind": "inflation", "start": "1979Q1", "end": "1980Q2",
     "note": "Supply disruption after the revolution, on top of already-elevated inflation expectations."},
    {"name": "Volcker disinflation", "kind": "growth", "start": "1981Q3", "end": "1982Q4",
     "end_note": "NBER trough November 1982.",
     "note": "The Fed drove the funds rate through 19% to break inflation. Two recessions in three years, and the reason a credible inflation-fighting central bank is priced differently."},
    {"name": "Gulf War oil spike", "kind": "inflation", "start": "1990Q3", "end": "1991Q1",
     "note": "Crude roughly doubled on the invasion of Kuwait, then gave it back quickly. A short, sharp supply shock."},
    {"name": "1990–91 recession", "kind": "growth", "start": "1990Q3", "end": "1991Q1",
     "note": "NBER peak July 1990 to trough March 1991."},
    {"name": "Dot-com bust", "kind": "growth", "start": "2001Q1", "end": "2001Q4",
     "note": "NBER peak March 2001 to trough November 2001. An equity and capex bust rather than a consumer one."},
    {"name": "Global financial crisis", "kind": "growth", "start": "2007Q4", "end": "2009Q2",
     "note": "NBER peak December 2007 to trough June 2009. The deepest contraction in the sample, and the episode most readers picture when they think about diversification failing."},
    {"name": "2008 commodity spike", "kind": "inflation", "start": "2007Q4", "end": "2008Q3",
     "note": "Crude peaked near $147 in July 2008, months into the recession — a reminder that an inflation shock and a growth shock can overlap."},
    {"name": "Post-GFC base effects", "kind": "inflation", "start": "2009Q4", "end": "2010Q2",
     "note": "⚠️ Not an event — an artefact. Year-on-year CPI swung from about −2% to +2.7% as the 2008 crash dropped out of the base, with no new inflation impulse. It clears the study's threshold and is therefore a derived episode, which is the honest cost of a rule nobody hand-picks: the year-on-year window can manufacture a surprise out of the comparison period alone."},
    {"name": "COVID-19 shutdown", "kind": "growth", "start": "2020Q1", "end": "2020Q2",
     "note": "NBER peak February 2020 to trough April 2020. The shortest recession on record and, by quarterly GDP, the sharpest."},
    {"name": "Post-COVID inflation surge", "kind": "inflation", "start": "2021Q2", "end": "2022Q4",
     "note": "Supply chains, goods demand and then energy after the invasion of Ukraine. US CPI peaked at 9.1% in June 2022 — the largest upside surprise in the modern sample."},
    {"name": "2022 tightening cycle", "kind": "growth", "start": "2022Q1", "end": "2022Q4",
     "note": "Not an NBER recession, but the growth metric's sharpest deterioration outside one — and the year stocks and bonds fell together, which is the problem this study exists for."},
]


def _quarter(value: str) -> pd.Period:
    return pd.Period(value, freq="Q")


def historical_overlaps(episode: Episode, minimum_quarters: int = 1) -> list[str]:
    """Names of the historical episodes a derived window overlaps.

    Matched on quarters, not on kind: an inflation window that coincides with a
    recession should say so, because the overlap is the interesting part — the
    1973 and 2008 pairs are both, at once.
    """
    names = []
    for item in HISTORICAL_EPISODES:
        start, end = _quarter(item["start"]), _quarter(item["end"])
        overlap = min(episode.end, end).ordinal - max(episode.start, start).ordinal + 1
        if overlap >= minimum_quarters:
            names.append(item["name"])
    return names


def historical_table() -> pd.DataFrame:
    """The named episodes as a frame, for display in the notebook."""
    return pd.DataFrame(
        [
            {
                "Episode": item["name"],
                "Kind": "Inflation" if item["kind"] == "inflation" else "Growth",
                "From": item["start"],
                "To": item["end"],
                "What happened": item["note"],
            }
            for item in HISTORICAL_EPISODES
        ]
    )
