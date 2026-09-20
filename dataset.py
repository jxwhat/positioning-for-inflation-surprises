"""Assembles the study's panel: macro inputs, forecasts, and asset returns.

The judgement calls all live here, each one flagged in its docstring, because
they are the places where this recreation departs from the 2022 original:

* the **pre-1981 CPI forecast**, spliced from the SPF's GDP-deflator question;
* the **commodity splice**, AQR's equal-weight series handed over to GSG;
* the **collateral leg** added to spot metals to mimic a futures total return;
* **treasury total returns**, reconstructed rather than taken from an index.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import bondmath
import metrics
import sources

#: The deck's study window for traditional assets. Real assets start 1976 there
#: only because Bloomberg's subindices do; our metals reach back to 1968.
STUDY_START = pd.Period("1972Q1", freq="Q")

#: AQR's commodity file ends here; after this we splice GSG. Checked 2026-09-17.
COMMODITY_SPLICE_TICKER = "GSG"


# --------------------------------------------------------------------------- #
# Macro levels and realised year-on-year rates
# --------------------------------------------------------------------------- #

def macro_levels() -> pd.DataFrame:
    """Quarterly CPI, core CPI and real GDP levels."""
    return pd.DataFrame(
        {
            "cpi": metrics.to_quarterly(sources.fred_series("CPIAUCNS")),
            "core_cpi": metrics.to_quarterly(sources.fred_series("CPILFENS")),
            "gdp": metrics.to_quarterly(sources.fred_series("GDPC1")),
        }
    )


# --------------------------------------------------------------------------- #
# Survey forecasts
# --------------------------------------------------------------------------- #

def _compound_annualised(rates_percent: pd.DataFrame) -> pd.Series:
    """Compound four annualised quarterly rates into one 4-quarter rate."""
    factors = 1.0 + rates_percent / 400.0
    return (factors.prod(axis=1, skipna=False) - 1.0) * 100.0


def inflation_forecast_1y(*, splice_pre_1981: bool = True) -> tuple[pd.Series, dict]:
    """One-year-ahead CPI forecast, indexed by the quarter it was made in.

    The SPF's CPI question only starts in **1981Q3**, which is a problem for a
    study that wants to begin in 1972: the Great Inflation is precisely where
    the upside-surprise observations live. AQR's paper also starts in 1972 on
    SPF forecasts without saying how it covered this gap (its footnote 13
    concerns long-term forecasts for synthetic TIPS, not this metric).

    Our fill uses the one SPF question that runs continuously from 1968Q4 — the
    GDP **price index** (``PGDP``) — and adds back the mean CPI-minus-deflator
    forecast wedge measured over the overlapping period. It is an assumption,
    not a measurement: CPI and the deflator differ in weighting and in their
    treatment of housing, and the wedge is not stable through time. The notebook
    reports the study both ways so the cost of the assumption is visible.
    """
    cpi_sheet = sources.spf_sheet("CPI")
    native = _compound_annualised(cpi_sheet[["CPI2", "CPI3", "CPI4", "CPI5"]]).dropna()

    deflator = sources.spf_sheet("PGDP")
    # PGDP columns are index *levels*: column 1 is the survey quarter, column 5
    # is four quarters later, so their ratio is the 4-quarter forecast.
    spliced_source = ((deflator["PGDP5"] / deflator["PGDP1"] - 1.0) * 100.0).dropna()

    overlap = pd.concat([native, spliced_source], axis=1, keys=["cpi", "pgdp"]).dropna()
    wedge = float((overlap["cpi"] - overlap["pgdp"]).mean())

    diagnostics = {
        "native_start": native.index.min(),
        "native_end": native.index.max(),
        "splice_start": spliced_source.index.min(),
        "wedge_pp": wedge,
        "overlap_quarters": len(overlap),
        "overlap_corr": float(overlap["cpi"].corr(overlap["pgdp"])),
        "wedge_std_pp": float((overlap["cpi"] - overlap["pgdp"]).std()),
    }

    if not splice_pre_1981:
        return native.rename("cpi_forecast_1y"), diagnostics

    backfill = (spliced_source + wedge).loc[: native.index.min() - 1]
    combined = pd.concat([backfill, native]).sort_index()
    return combined.rename("cpi_forecast_1y"), diagnostics


def growth_forecast_1y() -> pd.Series:
    """One-year-ahead real GDP growth forecast, from SPF median levels."""
    rgdp = sources.spf_sheet("RGDP")
    forecast = (rgdp["RGDP5"] / rgdp["RGDP1"] - 1.0) * 100.0
    return forecast.dropna().rename("gdp_forecast_1y")


# --------------------------------------------------------------------------- #
# Asset total returns, monthly
# --------------------------------------------------------------------------- #

def cash_monthly_return() -> pd.Series:
    """3-month T-bill, converted to a monthly return.

    ``TB3MS`` is a secondary-market **discount** rate, so this slightly
    understates a bond-equivalent yield. At the level of a collateral leg the
    difference is immaterial; it is not a substitute for a proper cash index.
    """
    bills = sources.fred_series("TB3MS")
    bills.index = pd.PeriodIndex(bills.index, freq="M")
    return (bills / 1200.0).rename("cash")


def equity_monthly_return() -> pd.Series:
    """CRSP value-weighted US market total return, from Ken French's factors.

    Replaces MSCI USA **Net** TR. This series is gross of dividend withholding
    tax, so it runs a few basis points a year rich to the original; it is also
    all-cap rather than large/mid. Neither materially affects a correlation.
    """
    factors = sources.ken_french("factors")
    return ((factors["Mkt-RF"] + factors["RF"]) / 100.0).rename("equities")


def treasury_monthly_returns() -> pd.DataFrame:
    """Par-bond total returns at 5, 10 and 20 year constant maturities.

    Uses the **daily** constant-maturity series sampled at month end, not
    FRED's monthly ``GS*`` series. That matters more than it looks: ``GS10`` is
    a monthly *average* of daily yields, so differencing it smears each month's
    yield move across two months. Checked against IEF over 2002-2026, the
    average-yield version correlates 0.72 with the ETF and the month-end
    version 0.99 — same formula, different sampling.

    ``DGS20`` is not continuous: Treasury stopped publishing a 20-year constant
    maturity between 1987 and 1993, so that column carries a gap.
    """
    out = {}
    for maturity, series_id in ((5, "DGS5"), (10, "DGS10"), (20, "DGS20")):
        daily = sources.fred_series(series_id)
        month_end = daily.groupby(pd.PeriodIndex(daily.index, freq="M")).last()
        out[f"ust_{maturity}y"] = bondmath.par_bond_monthly_returns(month_end, maturity)
    return pd.DataFrame(out)


def commodity_monthly_return(cash: pd.Series) -> tuple[pd.Series, dict]:
    """Equal-weight commodity total return: AQR excess return plus collateral.

    AQR's file stops well short of today, so the tail is spliced with GSG (the
    iShares S&P GSCI trust). The two are different animals — equal-weight
    versus production-weight, index versus fund — and the splice date is
    reported so every chart can mark it.
    """
    excess = sources.aqr_commodity_excess_return()
    total = (excess + cash.reindex(excess.index)).dropna()

    splice_from = total.index.max() + 1
    diagnostics = {"aqr_end": total.index.max(), "splice_ticker": COMMODITY_SPLICE_TICKER}
    try:
        etf = sources.yahoo_monthly_total_return(COMMODITY_SPLICE_TICKER)
    except Exception as error:  # offline, or Yahoo refusing — degrade, don't fail
        diagnostics["splice_error"] = str(error)
        return total.rename("commodities"), diagnostics

    overlap = pd.concat([total, etf], axis=1, keys=["aqr", "etf"]).dropna()
    diagnostics["overlap_months"] = len(overlap)
    diagnostics["overlap_corr"] = float(overlap["aqr"].corr(overlap["etf"]))
    tail = etf.loc[splice_from:]
    diagnostics["splice_start"] = tail.index.min() if len(tail) else None
    diagnostics["splice_months"] = len(tail)
    return pd.concat([total, tail]).rename("commodities"), diagnostics


def _month_end_price_return(daily_price: pd.Series) -> pd.Series:
    monthly = daily_price.copy()
    monthly.index = pd.PeriodIndex(monthly.index, freq="M")
    return monthly.groupby(level=0).last().pct_change()


def metals_monthly_returns(cash: pd.Series) -> pd.DataFrame:
    """Gold and precious-metals total returns from LBMA fixes plus collateral.

    The originals were Bloomberg's *subindex total return* series, which are
    fully-collateralised futures indices: excess return plus T-bill. Spot metal
    earns no collateral, so cash is added back to make the two comparable.
    Bloomberg's precious-metals subindex is gold and silver only, weighted
    roughly 80/20; we rebalance to those weights monthly.
    """
    gold = _month_end_price_return(sources.lbma_price("gold"))
    silver = _month_end_price_return(sources.lbma_price("silver"))
    blend = 0.8 * gold + 0.2 * silver
    frame = pd.DataFrame({"gold": gold, "precious_metals": blend})
    return frame.add(cash.reindex(frame.index), axis=0)


#: Fund sleeves for the backtesting app and the correlation charts. Their
#: histories start too late for the main study (Yahoo's fund data stops at
#: 1985 however old the fund), so they never enter Parts 3-4. All are total
#: returns, net of fund fees.
FUND_SLEEVES = {
    "ig_fund": "VWESX",    # Vanguard Long-Term Investment-Grade, 1985-
    "hy_fund": "VWEHX",    # Vanguard High-Yield Corporate, 1985-
    "em_debt": "FNMIX",    # Fidelity New Markets Income (USD EM sovereigns), 1993-
    "govt_fund": "FGOVX",  # Fidelity Government Income (Treasuries, agencies, agency MBS), 1985-
    "tips": "VIPSX",       # Vanguard Inflation-Protected Securities, 2000-
    "gsci": "GSG",         # iShares S&P GSCI Commodity-Indexed Trust, 2006-
}

#: Moody's seasoned Baa index holds bonds "as close as possible to 30 years".
IG_MODEL_MATURITY = 30


def ig_model_monthly_return() -> pd.Series:
    """US investment-grade credit, modelled: Moody's Baa yield as a 30y par bond.

    The same Swinkels approximation as the treasuries, so it inherits the same
    limits and adds two: no default or downgrade losses, and a duration far
    longer than a broad IG index. Month-end ``DBAA`` from 1986, when the daily
    series starts; before that FRED's ``BAA`` is a monthly *average*, the
    smoothing problem ``treasury_monthly_returns`` documents, so pre-1986
    returns are smeared across adjacent months.
    """
    daily = sources.fred_series("DBAA")
    month_end = daily.groupby(pd.PeriodIndex(daily.index, freq="M")).last()
    averages = sources.fred_series("BAA")
    averages.index = pd.PeriodIndex(averages.index, freq="M")
    yields = pd.concat([averages.loc[: month_end.index.min() - 1], month_end])
    return bondmath.par_bond_monthly_returns(yields, IG_MODEL_MATURITY).rename("ig_model")


def tbill_monthly_return() -> pd.Series:
    """One-month T-bill total return, from Ken French's research factors (``RF``).

    An actual monthly bill return back to 1926, so it serves both as the cash
    sleeve and as the risk-free rate for Sharpe and Sortino ratios. It tracks
    the ``TB3MS``-derived ``cash`` series closely (correlation 0.99, ~0.1pp a
    year apart since 1972); ``cash`` stays the collateral leg for the metals
    and commodities.
    """
    factors = sources.ken_french("factors")
    return (factors["RF"] / 100.0).rename("tbills")


def backtest_universe(monthly: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The study's panel plus the backtest-only sleeves (cash, modelled IG, funds).

    A fund Yahoo cannot serve is dropped and reported, not fatal.
    """
    frame = monthly.copy()
    frame["tbills"] = tbill_monthly_return()
    frame["ig_model"] = ig_model_monthly_return()
    missing = {}
    for sleeve, ticker in FUND_SLEEVES.items():
        try:
            frame[sleeve] = sources.yahoo_monthly_total_return(ticker)
        except Exception as error:  # offline, or Yahoo refusing
            missing[sleeve] = str(error)
    return frame.sort_index(), {"missing": missing}


def validate_ig_model() -> dict:
    """Check the modelled IG sleeve against the long-term IG fund it stands in for."""
    model = ig_model_monthly_return()
    try:
        fund = sources.yahoo_monthly_total_return(FUND_SLEEVES["ig_fund"])
    except Exception as error:
        return {"error": str(error)}
    both = pd.concat([model, fund], axis=1, keys=["model", "fund"]).dropna()
    return {
        "months": len(both),
        "correlation": float(both["model"].corr(both["fund"])),
        "model_annualised_vol": float(both["model"].std() * np.sqrt(12) * 100),
        "fund_annualised_vol": float(both["fund"].std() * np.sqrt(12) * 100),
    }


def monthly_asset_returns() -> tuple[pd.DataFrame, dict]:
    """The full monthly total-return panel, plus sourcing diagnostics."""
    cash = cash_monthly_return()
    commodities, commodity_notes = commodity_monthly_return(cash)

    frame = pd.concat(
        [
            equity_monthly_return(),
            treasury_monthly_returns(),
            commodities,
            metals_monthly_returns(cash),
            cash,
        ],
        axis=1,
    )

    reits = sources.nareit_all_equity_return()
    diagnostics = {"commodities": commodity_notes, "reits_available": reits is not None}
    if reits is not None:
        frame["reits"] = reits

    # The canonical 60/40, rebalanced monthly.
    frame["sixty_forty"] = 0.6 * frame["equities"] + 0.4 * frame["ust_10y"]
    return frame.sort_index(), diagnostics


# --------------------------------------------------------------------------- #
# Frequency conversion
# --------------------------------------------------------------------------- #

def quarterly_yoy_returns(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    """Overlapping year-on-year returns sampled quarterly, in percent.

    AQR's frequency choice: overlapping windows kill seasonality and blunt
    publication lags, at the price of serially correlated residuals.
    """
    wealth = (1.0 + monthly_returns).cumprod()
    quarterly = wealth.groupby(pd.PeriodIndex(wealth.index, freq="Q")).last()
    return (quarterly / quarterly.shift(4) - 1.0) * 100.0


def quarterly_returns(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    """Non-overlapping quarterly returns, in percent.

    Used for the tritile averages, which the deck reports per quarter rather
    than per year.
    """
    wealth = (1.0 + monthly_returns).cumprod()
    quarterly = wealth.groupby(pd.PeriodIndex(wealth.index, freq="Q")).last()
    return (quarterly / quarterly.shift(1) - 1.0) * 100.0


def validate_treasury_reconstruction() -> dict:
    """Check the 10-year reconstruction against IEF, the 7-10y treasury ETF.

    The reconstruction is the most homemade series in the study, so it gets an
    external check. IEF is 7-10 year laddered, not a constant-maturity 10-year
    par bond, so its volatility is lower — the correlation is the test, not the
    level.
    """
    reconstructed = treasury_monthly_returns()["ust_10y"]
    try:
        etf = sources.yahoo_monthly_total_return("IEF")
    except Exception as error:
        return {"error": str(error)}
    overlap = pd.concat([reconstructed, etf], axis=1, keys=["model", "ief"]).dropna()
    return {
        "months": len(overlap),
        "correlation": float(overlap["model"].corr(overlap["ief"])),
        "model_annualised_vol": float(overlap["model"].std() * np.sqrt(12) * 100),
        "ief_annualised_vol": float(overlap["ief"].std() * np.sqrt(12) * 100),
        "model_annualised_return": float(((1 + overlap["model"]).prod() ** (12 / len(overlap)) - 1) * 100),
        "ief_annualised_return": float(((1 + overlap["ief"]).prod() ** (12 / len(overlap)) - 1) * 100),
    }
