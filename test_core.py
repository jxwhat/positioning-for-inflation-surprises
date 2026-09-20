"""Tests for the parts of this study that are algebra rather than data.

Run with ``uv run pytest``. Nothing here touches the network: the loaders are
exercised by running the notebook, but the metric construction and the bond
math are where a silent sign error would quietly invalidate every exhibit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import bondmath
import metrics


def quarters(start: str, periods: int) -> pd.PeriodIndex:
    return pd.period_range(start, periods=periods, freq="Q")


# --------------------------------------------------------------------------- #
# Bond math
# --------------------------------------------------------------------------- #

def test_duration_and_convexity_match_closed_form():
    # A 10-year par bond at 5%: textbook values, and the check that caught the
    # deck's typeset convexity formula.
    assert bondmath.modified_duration(0.05, 10) == pytest.approx(7.795, abs=1e-3)
    assert bondmath.convexity(0.05, 10) == pytest.approx(73.63, abs=1e-2)


def test_duration_falls_as_yield_rises():
    ladder = [bondmath.modified_duration(y, 10) for y in (0.02, 0.05, 0.10, 0.15)]
    assert ladder == sorted(ladder, reverse=True)


def test_convexity_is_positive_across_plausible_yields():
    for yield_level in (0.005, 0.02, 0.05, 0.10, 0.20):
        assert bondmath.convexity(yield_level, 10) > 0


def test_flat_yields_return_the_coupon():
    # With no yield change, a par bond earns its yield, one twelfth per month.
    flat = pd.Series([5.0] * 6, index=pd.period_range("2020-01", periods=6, freq="M"))
    returns = bondmath.par_bond_monthly_returns(flat, 10)
    assert returns.iloc[0] != returns.iloc[0] or np.isnan(returns.iloc[0])  # first is NaN
    assert returns.iloc[1:].tolist() == pytest.approx([0.05 / 12] * 5)


def test_rising_yields_lose_money():
    rising = pd.Series([4.0, 5.0], index=pd.period_range("2020-01", periods=2, freq="M"))
    assert bondmath.par_bond_monthly_returns(rising, 10).iloc[1] < 0


# --------------------------------------------------------------------------- #
# Metric construction
# --------------------------------------------------------------------------- #

def test_yoy_percent_is_a_four_quarter_change():
    level = pd.Series([100.0, 101, 102, 103, 110], index=quarters("2020Q1", 5))
    assert metrics.yoy_percent(level).iloc[-1] == pytest.approx(10.0)


def test_to_quarterly_drops_a_quarter_with_missing_months():
    # July and August 2026 only: taking August as the Q3 level would make Q3's
    # year-on-year rate an eleven-month change.
    monthly = pd.Series(range(8), index=pd.date_range("2026-01-01", periods=8, freq="MS"), dtype=float)
    out = metrics.to_quarterly(monthly)
    assert list(out.index.astype(str)) == ["2026Q1", "2026Q2"]
    assert out.iloc[-1] == 5.0  # June


def test_to_quarterly_keeps_a_quarter_missing_a_middle_month():
    monthly = pd.Series(1.0, index=pd.date_range("2025-07-01", "2025-12-01", freq="MS")).drop(pd.Timestamp("2025-10-01"))
    assert list(metrics.to_quarterly(monthly).index.astype(str)) == ["2025Q3", "2025Q4"]


def test_to_quarterly_keeps_quarterly_input_whole():
    quarterly = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2026-01-01", periods=3, freq="QS"))
    assert len(metrics.to_quarterly(quarterly)) == 3


def test_change_metric_differences_four_quarters_back():
    yoy = pd.Series([1.0, 1, 1, 1, 3.5], index=quarters("2020Q1", 5))
    assert metrics.change_metric(yoy).iloc[-1] == pytest.approx(2.5)


def test_surprise_uses_the_forecast_made_four_quarters_earlier():
    yoy = pd.Series([np.nan] * 4 + [6.0], index=quarters("2020Q1", 5))
    forecast = pd.Series([2.0, 9, 9, 9, 9], index=quarters("2020Q1", 5))
    # The 2020Q1 forecast (2.0) is the one that predicted the 2021Q1 outturn.
    assert metrics.surprise_metric(yoy, forecast).iloc[-1] == pytest.approx(4.0)


def test_combine_equalises_the_two_standard_deviations():
    index = quarters("2000Q1", 80)
    generator = np.random.default_rng(0)
    change = pd.Series(generator.normal(0, 3, 80), index=index, name="change")
    surprise = pd.Series(generator.normal(0, 1, 80), index=index, name="surprise")
    frame = metrics.combine(change, surprise)
    assert frame["change"].std() == pytest.approx(frame["surprise_scaled"].std(), rel=1e-9)
    # And the combined leg is the plain average of the two equalised legs.
    assert frame["combined"].iloc[0] == pytest.approx(
        (frame["change"].iloc[0] + frame["surprise_scaled"].iloc[0]) / 2
    )


def test_combine_keeps_the_scale_it_used():
    index = quarters("2000Q1", 40)
    change = pd.Series(np.linspace(-4, 4, 40), index=index, name="change")
    surprise = pd.Series(np.linspace(-1, 1, 40), index=index, name="surprise")
    frame = metrics.combine(change, surprise)
    assert frame.attrs["surprise_scale"] == pytest.approx(4.0)


def test_classify_splits_on_the_z_score():
    index = quarters("2000Q1", 200)
    generator = np.random.default_rng(1)
    series = pd.Series(generator.normal(0, 1, 200), index=index)
    labels = metrics.classify(series, threshold=1.0)
    z = metrics.zscore(series)
    assert set(labels.unique()) <= {"upside", "stable", "downside"}
    assert (labels[z > 1] == "upside").all()
    assert (labels[z < -1] == "downside").all()
    assert (labels[(z >= -1) & (z <= 1)] == "stable").all()


def test_partial_correlation_equals_simple_when_control_is_orthogonal():
    index = quarters("1980Q1", 240)
    generator = np.random.default_rng(2)
    x = pd.Series(generator.normal(size=240), index=index)
    y = x * 0.5 + pd.Series(generator.normal(size=240), index=index)
    control = pd.Series(generator.normal(size=240), index=index)
    simple = y.corr(x)
    partial = metrics.partial_correlation(y, x, control)
    assert partial == pytest.approx(simple, abs=0.05)


def test_partial_correlation_removes_a_shared_driver():
    # y and x are related only through the control, so the partial should vanish.
    index = quarters("1980Q1", 240)
    generator = np.random.default_rng(3)
    control = pd.Series(generator.normal(size=240), index=index)
    x = control + pd.Series(generator.normal(0, 0.1, 240), index=index)
    y = control + pd.Series(generator.normal(0, 0.1, 240), index=index)
    assert abs(metrics.partial_correlation(y, x, control)) < 0.25
    assert y.corr(x) > 0.9


def test_hac_beta_is_the_correlation_without_a_control():
    index = quarters("1980Q1", 200)
    generator = np.random.default_rng(4)
    x = pd.Series(generator.normal(size=200), index=index)
    y = 0.4 * x + pd.Series(generator.normal(size=200), index=index)
    result = metrics.hac_significance(y, x)
    assert result["beta"] == pytest.approx(y.corr(x), abs=1e-9)
    assert result["nobs"] == 200


def test_hac_standard_errors_are_wider_than_naive_ones():
    # Overlapping windows: build a series with strong autocorrelation and check
    # the HAC t-statistic is the more conservative one.
    index = quarters("1960Q1", 300)
    generator = np.random.default_rng(5)
    noise = pd.Series(generator.normal(size=300), index=index)
    x = noise.rolling(4).mean().dropna()
    y = (0.3 * noise + generator.normal(0, 1, 300)).rolling(4).mean().dropna()
    hac = metrics.hac_significance(y, x, lags=3)
    naive = metrics.hac_significance(y, x, lags=0)
    assert abs(hac["tstat"]) < abs(naive["tstat"])


def test_sensitivity_table_shape_and_columns():
    index = quarters("1980Q1", 120)
    generator = np.random.default_rng(6)
    returns = pd.DataFrame(
        {"asset_a": generator.normal(size=120), "asset_b": generator.normal(size=120)},
        index=index,
    )
    inflation = metrics.combine(
        pd.Series(generator.normal(size=120), index=index, name="change"),
        pd.Series(generator.normal(size=120), index=index, name="surprise"),
    )
    growth = metrics.combine(
        pd.Series(generator.normal(size=120), index=index, name="change"),
        pd.Series(generator.normal(size=120), index=index, name="surprise"),
    )
    table = metrics.sensitivity_table(returns, inflation, growth)
    assert list(table.index) == ["asset_a", "asset_b"]
    for column in ("infl_combined", "growth_combined", "infl_partial", "infl_tstat", "nobs"):
        assert column in table.columns


# --------------------------------------------------------------------------- #
# NAREIT workbook parsing
#
# The workbook is a manual download and gitignored, so these skip rather than
# fail on a fresh clone. They are still worth having: the parser reads a column
# located by a three-row split header, and picking the wrong column would give
# a plausible-looking wrong answer.
# --------------------------------------------------------------------------- #

def test_nareit_returns_decimals_over_the_full_history():
    import sources

    series = sources.nareit_all_equity_return()
    if series is None:
        pytest.skip("no NAREIT workbook in manual/ — see sources.NAREIT_INSTRUCTIONS")

    assert isinstance(series.index, pd.PeriodIndex)
    assert series.index.freqstr == "M"
    assert str(series.index.min()) == "1972-01"
    assert len(series) > 600, "expected 50+ years of months"
    assert series.index.is_monotonic_increasing and series.index.is_unique
    # Decimals, not percent: the worst month in this index is about -32%, and a
    # missing /100 would put these in the tens.
    assert -0.5 < series.min() < 0.0
    assert 0.0 < series.max() < 0.5


def test_nareit_raises_on_an_unknown_column_group():
    import sources

    if sources.nareit_all_equity_return() is None:
        pytest.skip("no NAREIT workbook in manual/")
    with pytest.raises(RuntimeError, match="column group"):
        sources.nareit_all_equity_return(group="Not A Real Index Family")


# --------------------------------------------------------------------------- #
# Backtest app: horizons, availability, label placement
# --------------------------------------------------------------------------- #


def _toy_universe() -> pd.DataFrame:
    index = pd.period_range("1970-01", "2010-12", freq="M")
    frame = pd.DataFrame(0.01, index=index, columns=["equities", "ust_20y", "tips"])
    frame.loc[: pd.Period("1999-12", freq="M"), "tips"] = np.nan  # starts late
    frame.loc[pd.Period("1987-01", freq="M") : pd.Period("1993-09", freq="M"), "ust_20y"] = np.nan  # gap
    return frame


def test_available_sleeves_excludes_late_starts_and_gaps():
    import portfolio

    universe = _toy_universe()
    assert portfolio.available_sleeves(universe, "1972-01") == ["equities"]
    assert portfolio.available_sleeves(universe, "1995-01") == ["equities", "ust_20y"]
    assert portfolio.available_sleeves(universe, "2005-01") == ["equities", "ust_20y", "tips"]


def test_first_available_reports_the_month_after_a_gap():
    import portfolio

    universe = _toy_universe()
    assert portfolio.first_available(universe, "ust_20y") == "1993-10"
    assert portfolio.first_available(universe, "tips") == "2000-01"
    assert portfolio.first_available(universe, "equities") == "1970-01"


def test_label_positions_alternate_for_crowded_points():
    import charts

    positions = charts.label_positions([0.0, 0.01, 0.5], [0.0, 0.01, 0.5], span=1.0)
    assert positions[0] != positions[1], "neighbours must not share a label position"
    assert positions[2] == positions[0], "an isolated point keeps the default"


def test_summary_statistics_drawdowns_count_from_the_starting_value():
    import portfolio

    index = pd.period_range("2000-01", periods=4, freq="M")
    returns = pd.Series([-0.10, 0.05, 0.05, 0.02], index=index)
    stats = portfolio.summary_statistics(returns)
    # A first-month loss is a drawdown from the starting value of 1.
    assert stats["max_drawdown"] == pytest.approx(-0.10)
    # 0.9 -> 0.945 -> 0.99225 -> 1.012: underwater for three months, recovered in the fourth.
    assert stats["longest_drawdown_months"] == 3
    assert stats["positive_months"] == pytest.approx(0.75)


def test_summary_statistics_sharpe_is_excess_over_cash():
    import portfolio

    index = pd.period_range("2000-01", periods=24, freq="M")
    returns = pd.Series(np.tile([0.02, 0.0], 12), index=index)
    cash = pd.Series(0.01, index=index)
    stats = portfolio.summary_statistics(returns, cash)
    # Excess returns alternate +1% / -1%: mean zero, so Sharpe is zero.
    assert stats["sharpe"] == pytest.approx(0.0, abs=1e-12)
    assert stats["cash_return"] == pytest.approx(1.01**12 - 1)


def test_loaders_drop_the_month_they_were_fetched_in(tmp_path):
    import os
    import sources

    cache_file = tmp_path / "series.csv"
    cache_file.write_text("")
    fetched = pd.Timestamp("2026-09-17 12:00", tz="UTC").timestamp()
    os.utime(cache_file, (fetched, fetched))

    daily = pd.Series(1.0, index=pd.date_range("2026-08-28", "2026-09-16", freq="D"))
    assert sources._completed_months(daily, cache_file, "test").index.max() == pd.Timestamp("2026-08-31")

    monthly = pd.Series(1.0, index=pd.period_range("2026-07", "2026-09", freq="M"))
    assert str(sources._completed_months(monthly, cache_file, "test").index.max()) == "2026-08"
    assert sources.FETCHED["test"].startswith("2026-09-17T12:00:00")


# --------------------------------------------------------------------------- #
# Shock episodes
# --------------------------------------------------------------------------- #


def _metric_frame(values, start="1972Q1"):
    """A combine()-shaped frame whose combined column is exactly `values`."""
    index = pd.period_range(start, periods=len(values), freq="Q")
    return pd.DataFrame({"combined": pd.Series(values, index=index, dtype=float)})


def test_episodes_are_contiguous_runs_above_the_classifier_threshold():
    import episodes

    # Twelve quiet quarters, then a four-quarter spike, then quiet again. The
    # z-score is full-sample, so the spike has to be large to clear 1.0.
    values = [0.0] * 12 + [8.0, 9.0, 10.0, 7.0] + [0.0] * 12
    found = episodes.find_episodes(_metric_frame(values)["combined"], "inflation")
    assert len(found) == 1
    assert (str(found[0].start), str(found[0].end)) == ("1975Q1", "1975Q4")
    assert found[0].quarters == 4
    # The peak is the most extreme z-score inside the run, not the last one.
    assert found[0].peak > 1.0


def test_a_single_quarter_over_the_line_is_not_an_episode():
    import episodes

    values = [0.0] * 12 + [12.0] + [0.0] * 12
    assert episodes.find_episodes(_metric_frame(values)["combined"], "inflation") == []
    # ...unless the caller asks for one explicitly.
    assert len(episodes.find_episodes(_metric_frame(values)["combined"], "inflation", min_quarters=1)) == 1


def test_a_growth_episode_is_the_downside_tail():
    import episodes

    values = [0.0] * 12 + [-8.0, -9.0, -10.0] + [0.0] * 12
    assert episodes.find_episodes(_metric_frame(values)["combined"], "inflation") == []
    found = episodes.find_episodes(_metric_frame(values)["combined"], "growth")
    assert len(found) == 1 and found[0].peak < -1.0


def test_episode_classification_matches_the_studys_own_classifier():
    """The whole point of delegating: these cannot drift apart."""
    import episodes
    import metrics

    values = [0.0] * 10 + [8.0, 9.0, 10.0, 7.0] + [0.0] * 6 + [-9.0, -11.0] + [0.0] * 10
    combined = _metric_frame(values)["combined"]
    labels = metrics.classify(combined)
    for episode in episodes.find_episodes(combined, "inflation"):
        for quarter in pd.period_range(episode.start, episode.end, freq="Q"):
            assert labels[quarter] == "upside"


def test_episode_drawdown_starts_fresh_at_the_episode_and_catches_month_one():
    import episodes

    episode = episodes.Episode("inflation", pd.Period("2000Q1", "Q"), pd.Period("2000Q2", "Q"), 2.0)
    # A huge run-up BEFORE the episode must not become a peak the episode is
    # measured against; and the fall in the episode's own first month counts.
    index = pd.period_range("1999-01", "2000-06", freq="M")
    returns = pd.Series(0.0, index=index)
    returns.loc[pd.Period("1999-06", "M")] = 1.0  # +100% before the window
    returns.loc[pd.Period("2000-01", "M")] = -0.10  # first month of the episode
    returns.loc[pd.Period("2000-02", "M")] = -0.05

    result = episodes.performance(returns, episode)
    assert result["months"] == 6
    assert result["max_drawdown"] == pytest.approx(0.90 * 0.95 - 1.0)
    assert result["total_return"] == pytest.approx(0.90 * 0.95 - 1.0)
    assert result["covered"] is True


def test_a_series_starting_mid_episode_is_reported_but_flagged_uncovered():
    import episodes

    episode = episodes.Episode("growth", pd.Period("2000Q1", "Q"), pd.Period("2000Q4", "Q"), -2.0)
    late = pd.Series(0.01, index=pd.period_range("2000-07", "2000-12", freq="M"))
    result = episodes.performance(late, episode)
    assert result["months"] == 6
    assert result["covered"] is False

    missing = episodes.performance(pd.Series(0.01, index=pd.period_range("1990-01", "1990-12", freq="M")), episode)
    assert missing["months"] == 0 and missing["covered"] is False


def test_the_summary_excludes_partially_covered_episodes():
    import episodes

    early = episodes.Episode("growth", pd.Period("1990Q1", "Q"), pd.Period("1990Q2", "Q"), -2.0)
    late = episodes.Episode("growth", pd.Period("2000Q1", "Q"), pd.Period("2000Q2", "Q"), -2.0)
    # Covers only the second episode, so only that one may reach the average.
    series = pd.Series(-0.01, index=pd.period_range("2000-01", "2000-06", freq="M"))
    table = episodes.episode_table({"portfolio": series}, [early, late])
    summary = episodes.summarise(table)
    assert len(summary) == 1
    assert summary.iloc[0]["episodes"] == 1
    assert summary.iloc[0]["mean_return"] == pytest.approx(0.99**6 - 1)
