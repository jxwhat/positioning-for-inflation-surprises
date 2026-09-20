"""The inflation and growth surprise metrics, and the sensitivity statistics.

Methodology follows Thapar, Maloney and Brixton (2021), "When Stock-Bond
Diversification Fails", AQR Capital Management — the same source the original
2022 deck cites. Two measures of the *news* in a macro release:

1. **Change**  — year-on-year inflation minus year-on-year inflation a year
   earlier. A random-walk model of expectations.
2. **Surprise** — year-on-year inflation minus the one-year forecast made at the
   start of the period. Survey-based expectations.

Both are then scaled to a common standard deviation and averaged, so that
neither dominates the **Combined** metric through sheer magnitude. AQR's
footnote 3 is explicit about why: changes are larger than surprises, and asset
returns are more sensitive to surprises, so a raw average would underweight the
leg that matters most.

Everything is quarterly, with overlapping year-on-year windows. That choice
(AQR's) removes seasonality without seasonal adjustment and blunts publication
lags, at the cost of serial correlation in the residuals — which is why the
significance tests here are Newey-West corrected rather than naive.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

#: Overlapping 4-quarter windows induce autocorrelation out to 3 lags.
HAC_LAGS = 3


def to_quarterly(level: pd.Series) -> pd.Series:
    """Resample a monthly (or quarterly) index level to quarter-end observations.

    For monthly input a quarter counts only once its final month is in: a
    quarter-end value taken from its second month would make that quarter's
    year-on-year rate an eleven-month change. A missing month *inside* a
    quarter (BLS published no October 2025 CPI) does not matter.
    """
    out = level.dropna().copy()
    out.index = pd.PeriodIndex(out.index, freq="M")
    quarters = out.groupby(pd.PeriodIndex(out.index, freq="Q"))
    if quarters.size().max() == 1:  # already quarterly
        return quarters.last()
    last_month = pd.Series(out.index, index=out.index).groupby(pd.PeriodIndex(out.index, freq="Q")).last()
    complete = last_month.values == last_month.index.asfreq("M", how="end")
    return quarters.last()[complete]


def yoy_percent(quarterly_level: pd.Series) -> pd.Series:
    """Year-on-year percent change of a quarterly index level."""
    return (quarterly_level / quarterly_level.shift(4) - 1.0) * 100.0


def change_metric(yoy: pd.Series) -> pd.Series:
    """Year-on-year rate minus the year-on-year rate four quarters earlier."""
    return (yoy - yoy.shift(4)).rename("change")


def surprise_metric(yoy: pd.Series, forecast_1y: pd.Series) -> pd.Series:
    """Realised year-on-year rate minus the forecast made four quarters earlier.

    ``forecast_1y`` is indexed by the quarter in which the forecast was *made*
    and covers the following four quarters, so it is shifted forward to line up
    with the realisation it was predicting.
    """
    return (yoy - forecast_1y.shift(4)).rename("surprise")


def combine(change: pd.Series, surprise: pd.Series) -> pd.DataFrame:
    """Scale surprise to the standard deviation of change, then average.

    Scaling to *change*'s standard deviation rather than to 1 keeps the combined
    metric in percentage points, which is how the original deck plots it.
    """
    both = pd.concat([change, surprise], axis=1).dropna()
    scale = both["change"].std() / both["surprise"].std()
    frame = pd.concat([change, surprise * scale], axis=1)
    frame.columns = ["change", "surprise_scaled"]
    frame["combined"] = frame[["change", "surprise_scaled"]].mean(axis=1, skipna=False)
    frame["surprise_raw"] = surprise
    frame.attrs["surprise_scale"] = scale
    return frame


def zscore(series: pd.Series) -> pd.Series:
    """Full-sample z-score. In-sample by construction — see the notebook."""
    return (series - series.mean()) / series.std()


def classify(series: pd.Series, threshold: float = 1.0) -> pd.Series:
    """Tritile sort on the z-score: upside / stable / downside."""
    z = zscore(series)
    labels = pd.Series("stable", index=z.index, dtype=object)
    labels[z > threshold] = "upside"
    labels[z < -threshold] = "downside"
    return labels.where(z.notna()).rename("classification")


def partial_correlation(y: pd.Series, x: pd.Series, control: pd.Series) -> float:
    """Correlation of ``y`` and ``x`` with the linear effect of ``control`` removed."""
    frame = pd.concat([y, x, control], axis=1).dropna()
    if len(frame) < 12:
        return np.nan
    r = frame.corr().values
    r_yx, r_yz, r_xz = r[0, 1], r[0, 2], r[1, 2]
    denominator = np.sqrt((1 - r_yz**2) * (1 - r_xz**2))
    return np.nan if denominator == 0 else (r_yx - r_yz * r_xz) / denominator


def hac_significance(
    y: pd.Series,
    x: pd.Series,
    control: pd.Series | None = None,
    lags: int = HAC_LAGS,
) -> dict[str, float]:
    """Newey-West t-statistic for the sensitivity of ``y`` to ``x``.

    Both sides are standardised, so with no control the slope *is* the
    correlation. With a control the slope is the partial regression
    coefficient — close to, but not identical to, the partial correlation
    reported alongside it. The point of this function is the standard error,
    not the point estimate: overlapping year-on-year windows make naive
    p-values far too small.
    """
    columns = {"y": y, "x": x}
    if control is not None:
        columns["control"] = control
    frame = pd.concat(columns, axis=1).dropna()
    if len(frame) < 12:
        return {"beta": np.nan, "tstat": np.nan, "pvalue": np.nan, "nobs": len(frame)}
    standardised = (frame - frame.mean()) / frame.std()
    exog = sm.add_constant(standardised.drop(columns=["y"]))
    fit = sm.OLS(standardised["y"], exog).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True}
    )
    return {
        "beta": float(fit.params["x"]),
        "tstat": float(fit.tvalues["x"]),
        "pvalue": float(fit.pvalues["x"]),
        "nobs": int(fit.nobs),
    }


def sensitivity_table(
    asset_returns: pd.DataFrame,
    inflation: pd.DataFrame,
    growth: pd.DataFrame,
) -> pd.DataFrame:
    """Simple and partial correlations of every asset to both macro metrics.

    ``asset_returns`` holds overlapping year-on-year returns at quarterly
    frequency; ``inflation`` and ``growth`` are the frames returned by
    :func:`combine`.
    """
    legs = {"change": "change", "surprise": "surprise_scaled", "combined": "combined"}
    rows = []
    for asset in asset_returns.columns:
        returns = asset_returns[asset]
        row: dict[str, object] = {"asset": asset}
        for label, column in legs.items():
            row[f"infl_{label}"] = returns.corr(inflation[column])
            row[f"growth_{label}"] = returns.corr(growth[column])
        row["infl_partial"] = partial_correlation(
            returns, inflation["combined"], growth["combined"]
        )
        row["growth_partial"] = partial_correlation(
            returns, growth["combined"], inflation["combined"]
        )
        hac = hac_significance(returns, inflation["combined"], growth["combined"])
        row["infl_tstat"] = hac["tstat"]
        row["infl_pvalue"] = hac["pvalue"]
        row["nobs"] = hac["nobs"]
        rows.append(row)
    return pd.DataFrame(rows).set_index("asset")
