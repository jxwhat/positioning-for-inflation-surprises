"""Data acquisition for *Positioning for Inflation Surprises*.

Every loader here exists because the original 2022 study ran on a Bloomberg
terminal that is no longer available. The mapping from the original tickers to
these free replacements is documented in ``SOURCE_MAP`` below and reproduced in
the notebook's data-provenance table.

Design notes
------------
* Raw downloads are cached under ``cache/raw/``, parsed frames under ``cache/``.
  Nothing here costs money, so a cache miss fetches silently; pass
  ``refresh=True`` to force a re-download, or set ``REFRESH = True`` to force
  every loader at once.
* **Only completed months.** A daily series sampled at "month end" in the
  middle of a month, or a Yahoo monthly bar for the month in progress, is a
  partial month that looks like a whole one. Every loader drops observations
  dated in the month its data was fetched, judged by the cache file's time.
  ``FETCHED`` records that time per source, for "data as of" labels.
* ``_http_get`` refuses HTML bodies. The Philadelphia Fed serves a **soft 200**
  (an HTML page, not a 404) for any file path that does not exist, so a naive
  downloader silently caches a web page as ``.xlsx``. Verified 2026-09-17.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
RAW = CACHE / "raw"
MANUAL = HERE / "manual"
for _d in (CACHE, RAW, MANUAL):
    _d.mkdir(parents=True, exist_ok=True)

#: Force every loader to re-download, ignoring the cache.
REFRESH = False

#: When each source's data was fetched (ISO timestamps), filled as loaders run.
FETCHED: dict[str, str] = {}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
TIMEOUT = 60

#: Original Bloomberg/FRED ticker -> what we use instead, and why.
SOURCE_MAP = [
    # (sleeve, original source in the 2022 deck, replacement, first obs, note)
    ("Headline CPI", "Bloomberg CPI INDX Index", "FRED CPIAUCNS", "1913-01",
     "CPI-U, all items, not seasonally adjusted."),
    ("Core CPI", "Bloomberg CPI XYOY Index", "FRED CPILFENS", "1957-01",
     "All items less food and energy, NSA."),
    ("Real GDP", "Bloomberg GDP CYOY Index", "FRED GDPC1", "1947-01",
     "Chained 2017 dollars, SAAR; YoY computed here."),
    ("CPI forecast", "Philadelphia Fed SPF", "SPF medianLevel.xlsx, sheet CPI",
     "1981-Q3", "Quarterly annualised CPI forecasts. See PGDP splice below."),
    ("CPI forecast, pre-1981", "(not documented in the deck)",
     "SPF sheet PGDP + CPI-deflator wedge", "1968-Q4",
     "The SPF only began asking about CPI in 1981Q3; its GDP-deflator question "
     "runs continuously from 1968Q4."),
    ("GDP forecast", "Philadelphia Fed SPF", "SPF medianLevel.xlsx, sheet RGDP",
     "1968-Q4", "Median level forecasts; 4-quarter growth derived here."),
    ("US equities", "MSCI USA Net TR (NDDUUS Index)",
     "Ken French / CRSP value-weighted market + RF", "1926-07",
     "Gross of withholding tax, so slightly above a net-TR index."),
    ("US treasuries", "FRED constant-maturity yields", "FRED DGS5 / DGS10 / DGS20, month-end",
     "1962-01", "Par-bond total returns via Swinkels (2019); see Appendix A. "
     "DGS20 has a 1987-93 gap."),
    ("Commodities", "S&P GSCI TR (SPGSCITR Index)",
     "AQR Commodities for the Long Run (equal-weight) + T-bill", "1877-02",
     "Equal- rather than production-weight; AQR's Exhibit A1c puts the two at "
     "0.66 vs 0.67 inflation sensitivity. Spliced to GSG after 2025-05."),
    ("Gold", "Bloomberg Gold Subindex TR (BCOMGCTR)",
     "LBMA PM gold fix + T-bill collateral", "1968-04",
     "Collateral return added to match a fully-collateralised futures index."),
    ("Precious metals", "Bloomberg Precious Metals Subindex TR (BCOMPRTR)",
     "80/20 LBMA gold/silver + T-bill collateral", "1968-04",
     "Mirrors the gold/silver mix of a precious-metals index, roughly 80/20."),
    ("REITs", "FTSE NAREIT All Equity REITs TR (FNERTR)",
     "FTSE Nareit All Equity REITs TR, NAREIT workbook", "1972-01",
     "reit.com blocks scripted requests, so the file is downloaded by hand into manual/."),
    ("Cash / collateral", "n/a", "FRED TB3MS", "1934-01",
     "3M T-bill, used as the collateral leg and the risk-free rate."),
    # Backtest-only sleeves (Part 5 app and the correlation charts).
    ("Cash, 1m T-bills", "n/a", "Ken French / Ibbotson RF", "1926-07",
     "Backtest only. One-month T-bill total return; also the risk-free rate for Sharpe and Sortino."),
    ("IG credit, modelled", "n/a", "FRED BAA to 1985, month-end DBAA from 1986", "1919-01",
     "Backtest only. Moody's Baa yield as a 30y par bond; no default losses. Pre-1986 yields are "
     "monthly averages, so returns are smoothed."),
    ("IG credit fund", "n/a", "Yahoo VWESX", "1985-02",
     "Backtest only. Vanguard Long-Term Investment-Grade; net of fees."),
    ("High-yield fund", "n/a", "Yahoo VWEHX", "1985-02",
     "Backtest only. Vanguard High-Yield Corporate; net of fees."),
    ("EM debt fund", "n/a", "Yahoo FNMIX", "1993-06",
     "Backtest only. Fidelity New Markets Income, USD EM sovereigns; net of fees."),
    ("Government bond fund", "n/a", "Yahoo FGOVX", "1985-02",
     "Backtest only. Fidelity Government Income: Treasuries plus agency debt and agency MBS."),
    ("TIPS fund", "n/a", "Yahoo VIPSX", "2000-07",
     "Backtest only. Vanguard Inflation-Protected Securities; net of fees."),
    ("GSCI fund", "n/a", "Yahoo GSG", "2006-08",
     "Backtest only. iShares S&P GSCI Commodity-Indexed Trust: production-weighted, energy-heavy."),
]


def _env_value(key: str) -> str | None:
    """Read a key from the environment, else this folder's .env.local / .env.

    No extra dependencies: a ``KEY=value`` line is all the files need.
    """
    if os.environ.get(key):
        return os.environ[key].strip()
    for candidate in (HERE / ".env.local", HERE / ".env"):
        if candidate.exists():
            match = re.search(rf"^{key}=(.+)$", candidate.read_text(), re.M)
            if match:
                return match.group(1).strip().strip('"').strip("'")
    return None


def _fetched(path: Path, source: str) -> pd.Timestamp:
    """When ``path`` was downloaded; recorded in ``FETCHED`` under ``source``."""
    at = pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC")
    FETCHED[source] = at.isoformat(timespec="seconds")
    return at


def _completed_months(series: pd.Series, path: Path, source: str) -> pd.Series:
    """Drop observations dated in the month the data was fetched, or later."""
    fetch_month = _fetched(path, source).tz_localize(None).to_period("M")
    if isinstance(series.index, pd.PeriodIndex):
        return series[series.index.asfreq("M") < fetch_month]
    return series[series.index < fetch_month.start_time]


def _http_get(url: str, filename: str, *, refresh: bool = False) -> Path:
    """Download to cache/raw, refusing HTML bodies served in place of a file."""
    dest = RAW / filename
    if dest.exists() and not (refresh or REFRESH):
        return dest
    response = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    response.raise_for_status()
    body = response.content
    if body[:512].lstrip()[:1] in (b"<",):
        raise RuntimeError(
            f"{url} returned HTML, not a data file ({len(body)} bytes). "
            "Servers that soft-200 a missing path (e.g. the Philadelphia Fed) "
            "look like a success to requests.raise_for_status()."
        )
    dest.write_bytes(body)
    return dest


# --------------------------------------------------------------------------- #
# FRED
# --------------------------------------------------------------------------- #

def fred_series(series_id: str, *, refresh: bool = False) -> pd.Series:
    """One FRED series as a float Series indexed by observation date."""
    cached = CACHE / f"fred_{series_id}.csv"
    if cached.exists() and not (refresh or REFRESH):
        out = pd.read_csv(cached, index_col=0, parse_dates=True).iloc[:, 0]
        return _completed_months(out, cached, f"FRED {series_id}")

    key = _env_value("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY not found: set it in the environment, or put FRED_API_KEY=... in a "
            ".env.local file next to this module (free key: https://fred.stlouisfed.org/docs/api/api_key.html)"
        )
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": key, "file_type": "json"},
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    frame = pd.DataFrame(response.json()["observations"])
    # FRED encodes a missing observation as "." rather than null.
    frame = frame[frame["value"] != "."]
    out = pd.Series(
        frame["value"].astype(float).values,
        index=pd.to_datetime(frame["date"]),
        name=series_id,
    )
    out.to_frame().to_csv(cached)
    return _completed_months(out, cached, f"FRED {series_id}")


# --------------------------------------------------------------------------- #
# Philadelphia Fed — Survey of Professional Forecasters
# --------------------------------------------------------------------------- #

SPF_URL = (
    "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/"
    "survey-of-professional-forecasters/historical-data/medianlevel.xlsx"
)


def spf_sheet(sheet: str, *, refresh: bool = False) -> pd.DataFrame:
    """One SPF median-forecast sheet, indexed by survey quarter.

    Column *n* of a sheet is the forecast for the survey quarter (n=1) and the
    following five quarters (n=2..6); the letter columns are annual averages.
    """
    path = _http_get(SPF_URL, "spf_medianlevel.xlsx", refresh=refresh)
    _fetched(path, "Philadelphia Fed SPF")
    frame = pd.read_excel(path, sheet_name=sheet)
    index = pd.PeriodIndex(
        [
            f"{int(y)}Q{int(q)}"
            for y, q in zip(frame["YEAR"], frame["QUARTER"], strict=True)
        ],
        freq="Q",
    )
    frame = frame.drop(columns=["YEAR", "QUARTER"]).set_axis(index)
    return frame.apply(pd.to_numeric, errors="coerce")


# --------------------------------------------------------------------------- #
# LBMA precious metal fixes
# --------------------------------------------------------------------------- #

LBMA_URLS = {
    "gold": "https://prices.lbma.org.uk/json/gold_pm.json",
    "silver": "https://prices.lbma.org.uk/json/silver.json",
}


def lbma_price(metal: str, *, refresh: bool = False) -> pd.Series:
    """Daily USD fix for 'gold' (PM fix) or 'silver', from 1968."""
    path = _http_get(LBMA_URLS[metal], f"lbma_{metal}.json", refresh=refresh)
    records = json.loads(path.read_text())
    dates, values = [], []
    for row in records:
        usd = row["v"][0] if row.get("v") else None
        if usd:  # the feed carries holiday rows with null/zero values
            dates.append(row["d"])
            values.append(float(usd))
    out = pd.Series(values, index=pd.to_datetime(dates), name=f"{metal}_usd").sort_index()
    return _completed_months(out, path, f"LBMA {metal}")


# --------------------------------------------------------------------------- #
# Ken French data library
# --------------------------------------------------------------------------- #

FF_URLS = {
    "factors": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
               "F-F_Research_Data_Factors_CSV.zip",
    "portfolios_6": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
                    "6_Portfolios_2x3_CSV.zip",
}


def ken_french(dataset: str, *, refresh: bool = False) -> pd.DataFrame:
    """First (monthly, value-weighted) block of a Ken French CSV, in percent.

    The files carry several stacked blocks — monthly then annual, value- then
    equal-weighted — separated by blank lines. We take the first.
    """
    path = _http_get(FF_URLS[dataset], f"ken_french_{dataset}.zip", refresh=refresh)
    _fetched(path, f"Ken French {dataset}")
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        text = archive.read(name).decode("latin-1")

    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(r"^\s*,", line))
    rows = []
    for line in lines[start + 1:]:
        if not re.match(r"^\s*\d{6}\s*,", line):  # end of the monthly block
            if rows:
                break
            continue
        rows.append(line)

    frame = pd.read_csv(io.StringIO("\n".join([lines[start]] + rows)))
    frame.columns = ["period"] + [c.strip() for c in frame.columns[1:]]
    frame = frame.set_index(
        pd.PeriodIndex(frame["period"].astype(int).astype(str), freq="M")
    ).drop(columns=["period"])
    return frame.apply(pd.to_numeric, errors="coerce")


# --------------------------------------------------------------------------- #
# AQR — Commodities for the Long Run
# --------------------------------------------------------------------------- #

AQR_COMMODITIES_URL = (
    "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
    "Commodities-for-the-Long-Run-Index-Level-Data-Monthly.xlsx"
)


def aqr_commodity_excess_return(*, refresh: bool = False) -> pd.Series:
    """Monthly excess return of AQR's equal-weight commodity portfolio, 1877-.

    Levine, Ooi, Richardson and Sasseville (2018), "Commodities for the Long
    Run", Financial Analysts Journal 74(2). Returns are decimals, in excess of
    cash, so the collateral leg must be added back for a total return.
    """
    path = _http_get(AQR_COMMODITIES_URL, "aqr_commodities.xlsx", refresh=refresh)
    _fetched(path, "AQR commodities")
    raw = pd.read_excel(path, sheet_name="Commodities for the Long Run", header=None)
    header_row = raw.index[
        raw[1].astype(str).str.contains("Excess return of equal-weight", na=False)
    ][0]
    body = raw.loc[header_row + 1:, [0, 1]].copy()
    body.columns = ["date", "excess_return"]
    body["date"] = pd.to_datetime(body["date"], errors="coerce")
    body["excess_return"] = pd.to_numeric(body["excess_return"], errors="coerce")
    body = body.dropna()
    return pd.Series(
        body["excess_return"].values,
        index=pd.PeriodIndex(body["date"], freq="M"),
        name="commodities_excess",
    )


# --------------------------------------------------------------------------- #
# Yahoo — only for the post-2025 commodity splice and the ETF appendix
# --------------------------------------------------------------------------- #

def yahoo_monthly_total_return(ticker: str, *, refresh: bool = False) -> pd.Series:
    """Month-end total return from Yahoo, via yfinance's cookie/crumb handling.

    Naked HTTP against Yahoo gets rate-limited; always go through the library.
    """
    cached = CACHE / f"yahoo_{ticker.replace('^', '').replace('=', '')}.csv"
    if cached.exists() and not (refresh or REFRESH):
        series = pd.read_csv(cached, index_col=0).iloc[:, 0]
        series.index = pd.PeriodIndex(series.index, freq="M")
        return _completed_months(series, cached, f"Yahoo {ticker}")

    import yfinance as yf

    history = yf.Ticker(ticker).history(period="max", interval="1mo", auto_adjust=True)
    if history.empty:
        raise RuntimeError(f"Yahoo returned no history for {ticker}")
    closes = history["Close"].dropna()
    closes.index = pd.PeriodIndex(closes.index, freq="M")
    out = closes.groupby(level=0).last().pct_change().dropna()
    out.name = ticker
    out.to_frame().to_csv(cached)
    return _completed_months(out, cached, f"Yahoo {ticker}")


# --------------------------------------------------------------------------- #
# NAREIT — manual download (reit.com is behind a fingerprint wall)
# --------------------------------------------------------------------------- #

NAREIT_INSTRUCTIONS = f"""\
REIT data needs one manual download (reit.com blocks automated requests):

  1. open https://www.reit.com/data-research/reit-market-data/report/monthly-index-values-returns
  2. take "Monthly Historical Index Data: 1972 - 2026"
     (https://www.reit.com/sites/default/files/returns/MonthlyHistoricalReturns.xls)
     — NOT "Monthly Index Data: 2026", which is the current year only
  3. save it into {MANUAL}/  (any name containing "nareit", .xls or .xlsx)

The direct file URL is walled too — verified 2026-09-18 with a browser User-Agent
and a matching Referer, both of which still return the 3KB challenge page. It has
to come from a real browser.

The REIT sleeve is skipped until that file exists; everything else runs.\
"""


#: Layout of NAREIT's "Monthly Historical Index Data" workbook, verified against
#: the 1971-12 → 2026-08 vintage downloaded 2026-09-18. The sheet carries six
#: index families side by side, each a seven-column block under a single group
#: label, and the header is split across three rows: the group name, then
#: "Total"/"Price"/"Income" on the next, then "Return"/"Index"/"Yield" below it.
NAREIT_SHEET = "Index Data"
NAREIT_GROUP = "All Equity REITs"


def nareit_all_equity_return(*, group: str = NAREIT_GROUP) -> pd.Series | None:
    """Monthly total return of the FTSE NAREIT All Equity REITs index.

    Returns ``None`` when the manual file is absent, so the notebook degrades to
    "no REIT sleeve" rather than failing. Raises when the file is present but
    does not look like the workbook this was written against — a wrong answer
    here would be indistinguishable from a real result, so it is worth failing
    loudly on a layout change.

    NAREIT publishes the monthly total return directly, in percent, so it is
    read rather than differenced out of the index level.
    """
    candidates = sorted(
        p for p in MANUAL.glob("*")
        if "nareit" in p.name.lower() and p.suffix.lower() in {".xls", ".xlsx"}
    )
    if not candidates:
        return None
    path = candidates[-1]

    sheets = pd.ExcelFile(path).sheet_names
    if NAREIT_SHEET not in sheets:
        raise RuntimeError(
            f"{path.name}: expected a {NAREIT_SHEET!r} sheet, found {sheets}. "
            "Is this the 'Monthly Historical Index Data' workbook?"
        )
    frame = pd.read_excel(path, sheet_name=NAREIT_SHEET, header=None)

    header_row = column = None
    for row in range(min(12, len(frame))):
        for col, value in frame.iloc[row].items():
            if isinstance(value, str) and value.strip() == group:
                header_row, column = row, col
                break
        if column is not None:
            break
    if column is None:
        groups = [
            v.strip() for v in frame.iloc[:12].to_numpy().ravel()
            if isinstance(v, str) and v.strip()
        ]
        raise RuntimeError(
            f"{path.name}: no {group!r} column group. Groups seen: {groups}"
        )

    # The group's first sub-column is its total return; confirm before trusting it.
    label = tuple(
        str(frame.iloc[header_row + offset, column]).strip().lower()
        for offset in (1, 2)
    )
    if label != ("total", "return"):
        raise RuntimeError(
            f"{path.name}: expected a Total Return sub-column under {group!r} "
            f"at column {column}, found {label}."
        )

    body = frame.loc[header_row + 3:, [0, column]].copy()
    body.columns = ["date", "total_return_percent"]
    body["date"] = pd.to_datetime(body["date"], errors="coerce")
    body["total_return_percent"] = pd.to_numeric(
        body["total_return_percent"], errors="coerce"
    )
    body = body.dropna()
    if len(body) < 480:  # this file should carry 50+ years of months
        raise RuntimeError(
            f"{path.name}: only {len(body)} monthly observations under {group!r}. "
            "This looks like the current-year file, not the historical one."
        )

    return pd.Series(
        body["total_return_percent"].values / 100.0,
        index=pd.PeriodIndex(body["date"], freq="M"),
        name="reits",
    ).groupby(level=0).last()
