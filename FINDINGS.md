# Findings — Positioning for Inflation Surprises

**Recreation of a weekly investment meeting deck of 9 March 2022, built 17–18
September 2026.** All figures below are from the study as committed; re-running it will move
the last few quarters as data revises.

## What this file is, and how it relates to the others

| File | Holds |
|---|---|
| `positioning-for-inflation-surprises.ipynb` | the study itself — the argument, in order, with its exhibits |
| **`FINDINGS.md`** (this file) | **the findings register**: every substantive thing established, including the parts that do not fit the notebook's narrative — discrepancies against the original, bugs, dead ends, open questions |
| `README.md` | how to run it |

The notebook is written to be read. This file is written to be *searched* — by a future session,
or by whoever asks "did we already check that?".

---

## 1. Replication: what held, what did not

### 1.1 Sensitivities — the core result, and it replicates

Partial correlation to the combined inflation metric, controlling for growth; quarterly,
overlapping year-on-year windows, 1972Q1 to present.

| Sleeve | Inflation, ours | Inflation, deck | Growth, ours | Growth, deck | NW *t* (inflation) |
|---|---|---|---|---|---|
| US equities | −0.20 | −0.21 | +0.45 | +0.40 | −1.83 |
| UST 10y | −0.47 | −0.43 | −0.21 | −0.26 | −4.53 |
| 60/40 | −0.35 | −0.34 | +0.36 | +0.23 | −2.90 |
| Commodities | +0.64 | +0.60 | +0.19 | +0.25 | +5.44 |
| Gold | +0.49 | +0.50 | −0.23 | −0.20 | +3.17 |
| Precious metals | +0.49 | +0.48 | −0.20 | −0.15 | +2.97 |
| REITs | −0.02 | −0.03 | +0.39 | +0.35 | −0.15 |

Every sign matches and every magnitude is within ~0.06, on independently sourced data, with
4½ years of extra sample. **The study's conclusions do not depend on Bloomberg.**

### 1.2 What did not replicate: the portfolio panel's absolute statistics

Deck weights (60% equities / 25% UST 10y / 10% commodities / 15% gold), 1972-01 onward:

| | Deck (slide 28) | Ours, normalised | Ours, as given (gross 110%) |
|---|---|---|---|
| Annualised return | 9.08% | 10.88% | 11.97% |
| Volatility | 7.53% | 9.77% | 10.75% |
| Max drawdown | −15.34% | −28.68% | −31.18% |
| Sharpe (rf 1.5%) | 1.01 | 0.96 | 0.97 |

Richer and riskier on every measure. Three identified causes, in order of size:

1. **The equity proxy.** CRSP's all-cap value-weighted market runs 15.7% annualised volatility
   against MSCI USA large/mid's ~14–15%, and returns more. At ~55% weight this accounts for
   most of both gaps.
2. **The commodity proxy.** AQR's equal-weight series had a far better 1970s than the
   production-weighted GSCI.
3. **Drawdown measurement.** Our trough is **2009-02**. A ~55%-equity portfolio cannot have
   drawn down 15% through the GFC on monthly data. Sampling the wealth curve quarterly — which
   is the frequency the original's data was at — narrows it to **−24.1%**; the residual is
   probably the equity proxy again.

Not chased further: closing it would mean reverse-engineering index choices that are not visible
in the PDF, and it changes no conclusion. **Open question**, see §8.

### 1.3 What the slide-28 exercise was actually demonstrating — and it works

At the deck's own weights the blend prints an inflation partial correlation of **−0.013**
against 60/40's **−0.345**, while keeping **+0.318** to growth. That is the entire point of the
exhibit and it reproduces cleanly: the inflation exposure can be neutralised without giving up
the growth exposure.

---

## 2. Substantive findings about the assets

### 2.1 The diagonal is the useful fact

The macro map splits into two occupied diagonals:

- **Left half** — equities (−0.20, +0.45), 60/40 (−0.35, +0.36), UST 10y (−0.47, −0.21):
  negative to inflation, split on growth.
- **Top-right** — commodities (+0.64, +0.19): positive to inflation *and* to growth. Diversifies
  the inflation exposure while adding to a growth exposure the portfolio already has.
- **Bottom-right** — gold (+0.49, −0.23), precious metals (+0.49, −0.20): positive to inflation,
  negative to growth. **The quadrant diagonally opposite equities**, and therefore the
  genuinely complementary one.

An allocation wanting to cut inflation sensitivity *without* doubling down on growth wants the
bottom-right; one happy to take growth risk for a higher long-run premium wants the top-right.
Same trade-off AQR frames as commodities versus breakevens.

### 2.2 Equities: real but small, and the significance depends on the horizon

This is the one conclusion that changed during the build, twice. See §3.2 for the full table.
The settled statement:

> Equities' negative sensitivity to inflation news is **real but small** — too small for ~55
> independent years to resolve at the year-on-year horizon (*t* = −1.83), large enough for 655
> months to (*t* = −2.76). The sign is stable across every specification tried and agrees with
> AQR's independent estimate on a different equity proxy.

This is a weaker claim than the deck's first bullet. The bond claim is the unambiguous one.

### 2.3 Bonds: the robust half of the central result

UST 10y at −0.47 partial, *t* = −4.53, significant at every horizon tested. Intuitive: a claim
on a fixed set of nominal cash flows is worth less when the price level surprises upward. **If
only one finding from this study survives scrutiny, it is this one**, and it is enough to carry
the 60/40 argument on its own (the 60/40 prints −0.35 at *t* = −2.90).

### 2.4 Commodities and metals are not interchangeable

Both carry positive inflation sensitivity, but they sit on opposite sides of the growth axis
(§2.1). Commodities also show the largest *magnitude* of any sleeve (+0.64) and the strongest
statistic (*t* = +5.44).

### 2.5 REITs: near-zero linear sensitivity concealing a bad upside tail

**The one finding that genuinely changed with the extra four years.** The deck read REITs as
holding up in *both* tails — 4.4% in upside-surprise quarters, 5.6% in downside — and hedged
that this "may be circumstantial". That hedge was right.

Average quarterly return in upside-surprise quarters:

| Window | REITs, upside |
|---|---|
| 1976Q1–2021Q4 (the deck's) | 3.20% |
| 1972Q1–present (full) | **0.40%** |

The cause is specific and identifiable: 2022Q1 **−5.3%**, 2022Q2 **−14.7%**, 2022Q3 **−10.8%**,
all three classed as upside-surprise quarters — roughly −24% compounded across the last two.
The largest inflation surprise in fifty years arrived as a rate shock, and a levered,
long-duration, income-paying asset class behaved accordingly.

So: **near-zero *linear* sensitivity to inflation news (−0.02), but the flat average hides
precisely the tail an investor buying REITs for inflation protection cares about.** The
correlation was never wrong; it was the wrong statistic to take comfort from. REITs are better
described as equity-like growth exposure (+0.39 to growth) wearing a real-asset label.

### 2.6 The tail asymmetry, in return terms

Average quarterly return by regime, 1972Q1–present (25 upside / 168 stable / 25 downside
quarters out of 218; updated 2026-09-19 once partial periods were dropped, see §3.6 — the partial
2026Q3 had been an upside quarter):

| Sleeve | Upside surprise | Stable | Downside surprise | Upside − downside |
|---|---|---|---|---|
| US equities | −1.56% | 3.61% | 4.17% | −5.73pp |
| UST 10y | 0.44% | 1.44% | 3.93% | −3.49pp |
| 60/40 | −0.76% | 2.71% | 4.02% | −4.78pp |
| Commodities | 6.07% | 2.36% | 0.36% | +5.71pp |
| Gold | 10.94% | 3.09% | 0.64% | +10.30pp |
| Precious metals | 10.87% | 3.20% | 0.73% | +10.14pp |
| REITs | 0.26% | 3.37% | 3.66% | −3.40pp |

Equities versus gold is a ~12-point swing **per quarter** between the two tails. Note also the
"frown" AQR describes: equities are worst in the upside column but strong in the downside
column, because falling inflation in this sample usually arrived with a growth shock.

---

## 3. Methodological findings

### 3.1 Three frequencies, used for three different jobs

A recurring source of confusion, so stated explicitly:

| Frequency | Where it is used | Why |
|---|---|---|
| **Monthly total returns** | the raw material for everything; the portfolio panel exclusively (monthly rebalancing, and all of return/vol/drawdown/Sharpe) | it is the finest frequency every sleeve supports |
| **Overlapping year-on-year, sampled quarterly** | every sensitivity: correlations, partial correlations, the macro map | horizon match — see below |
| **Non-overlapping quarterly** | the tritile regime averages | the deck reports these per quarter (its axes say so) |

The year-on-year choice for sensitivities is not arbitrary:

1. **The metric is intrinsically a 12-month object** — year-on-year CPI minus year-on-year CPI a
   year earlier, and year-on-year CPI minus the year-ago one-year forecast. Correlating a
   twelve-month news measure against a one-month return is a horizon mismatch.
2. **It is AQR's specification**, stated on p.2 of their paper: *"By focusing on quarterly
   overlapping year-on-year periods, we avoid seasonal effects and mitigate the role of
   publication lags."*
3. **The original deck did the same** — slide 34's axes read "Equities returns (YoY%)" and
   "Treasuries returns (YoY%)" against the inflation metric, while slides 16 and 21 label their
   bar axis "Asset returns (Quarterly)". The deck used all three frequencies too.

### 3.2 Horizon robustness — and the conclusion it revised

The same test at three return horizons. Correlation to the combined inflation metric, with the
Newey-West *t*-statistic (growth controlled) beneath:

| Sleeve | YoY overlap (n=219) | Quarterly, non-overlapping (n=219) | Monthly (n=655) |
|---|---|---|---|
| US equities | −0.19 *(t −1.83)* | −0.20 *(t −2.47)* | −0.13 *(t −2.76)* |
| UST 10y | −0.46 *(t −4.53)* | −0.21 *(t −2.40)* | −0.14 *(t −2.61)* |
| 60/40 | −0.33 *(t −2.90)* | −0.26 *(t −2.97)* | −0.16 *(t −3.45)* |
| Commodities | +0.63 *(t 5.44)* | +0.20 *(t 2.72)* | +0.13 *(t 2.52)* |
| Gold | +0.48 *(t 3.17)* | +0.23 *(t 2.33)* | +0.14 *(t 2.28)* |
| Precious metals | +0.48 *(t 2.97)* | +0.21 *(t 1.95)* | +0.12 *(t 1.91)* |
| REITs | −0.02 *(t −0.15)* | −0.14 | −0.08 |

Two readings, and the second one matters:

- **Signs never move; magnitudes shrink as the horizon shortens.** Mechanical — a slow annual
  news measure explains far less of one month's return than of one year's. It does *not* mean
  the year-on-year figures are inflated; they are the correlation at the horizon the signal
  operates on.
- **Significance moves the *other* way**, because shortening the horizon gains observations
  faster than it loses correlation. Equities: −1.83 → −2.47 → −2.76.

Consequence: a claim of the form "X does not survive the correction" must name its horizon. The
equity result is significant at the shorter horizons and not at the one AQR's specification
uses — which is the specification with the least power to resolve a small effect.

**Caveat on the monthly column.** The metric is quarterly, so it is held flat across each
quarter's three months. That repeats information rather than adding it; the Newey-West lags
absorb some of it. The non-overlapping quarterly column is the clean comparison.

### 3.3 Overlapping windows make naive standard errors badly wrong

Consecutive observations share three quarters of data, so residuals are strongly
autocorrelated. All inference here is Newey-West with 3 lags (the autocorrelation the overlap
mechanically induces). This was added as an improvement on the original, and it is the reason
§2.2 exists — a naive standard error would have reported the equity result as comfortably
significant at every horizon.

### 3.4 The pre-1981 forecast splice — the one real assumption

**The SPF only began asking its panel about CPI in 1981Q3.** A study starting in 1972 therefore
has no survey forecast for its first decade — which is exactly where the upside-surprise
observations live.

**AQR does not disclose how it covered this gap.** Its paper starts in January 1972, credits the
SPF, and defines the surprise as year-on-year inflation minus "1-year forecast 12 months earlier"
(Exhibit 1 source note) — nothing more. *Corrected 2026-09-18:* an earlier version of this section
said AQR stitched Kozicki-Tinsley estimates and several surveys together (its footnote 13). That
footnote is about the long-term inflation forecasts behind AQR's synthetic TIPS returns, not the
surprise metric; the claim was a misreading, repeated in the notebook and `dataset.py`, and is
fixed in all three. A deflator-based fill like ours is one plausible guess at what AQR did
silently; the paper cannot confirm it.

The fill: the one SPF question that runs continuously from **1968Q4** — the **GDP price index**
(`PGDP`) — plus the mean CPI-minus-deflator forecast wedge over the overlap.

| Diagnostic | Value |
|---|---|
| Overlap where both exist | 181 quarters (1981Q3–2026Q3) |
| Correlation of the two forecasts | **0.964** |
| Mean wedge (added to the fill) | **+0.300pp** |
| Standard deviation of the wedge | **0.324pp** |

Read honestly: the *level* of the fill is well founded (0.96 correlation), and its
quarter-to-quarter error is **not** negligible — the wedge's dispersion is about the size of its
mean. CPI and the deflator differ in weighting and in their treatment of shelter, and the wedge
is not stable through time.

**If you distrust it, every number in this study still holds from 1981Q3 onward.** The notebook
computes and plots both versions. What you lose is the 1970s, which is the trade the deck's
"choice of study period" slide was about.

### 3.5 The 1976-versus-1972 window explains the tritile gap

The deck's real-asset exhibits ran from **1976**, not 1972 — its Bloomberg subindices started
there. Our metals reach back to 1968 and the commodity series to 1877, so we have no data reason
to start at 1976, but the comparison matters for judging fidelity:

| Sleeve (avg quarterly return, upside / stable / downside) | Ours, 1972Q1– | Ours, 1976Q1–2021Q4 | Deck reported |
|---|---|---|---|
| Commodities | 6.07 / 2.36 / 0.36 | 3.56 / 1.84 / 0.50 | 4.6 / 1.8 / 1.2 |
| Gold | 10.94 / 3.09 / 0.64 | 9.94 / 1.79 / 2.08 | 8.7 / 1.1 / 1.2 |
| Precious metals | 10.87 / 3.20 / 0.73 | 9.79 / 1.94 / 2.00 | 9.3 / 1.0 / 1.5 |
| REITs | 0.26 / 3.37 / 3.66 | 3.20 / 3.64 / 3.75 | 4.4 / 3.2 / 5.6 |

On the deck's own window the numbers converge. **The residual is what the proxy substitutions
cost, and it is small enough to leave the conclusions where they are** — except for REITs,
where the difference is the 2022 data itself (§2.5).

### 3.6 Metric construction facts worth knowing

_Updated 2026-09-19: loaders now keep **completed periods only**. The metric had been using a
partial 2026Q3 (July and August CPI measured against a full 2025Q3), and several monthly sleeves
included a half-finished September. Dropping them moved each σ below by 0.01pp and the latest
quarter to 2026Q2; no conclusion changes. A quarter still counts when a month inside it is
missing (BLS published no October 2025 CPI), because only the quarter-end level is used._

| Quantity | Value |
|---|---|
| σ(change) | 2.24pp |
| σ(surprise), unscaled | 2.06pp |
| Scaling factor λ applied to surprise | 1.082 |
| σ(combined) | 2.12pp |
| corr(change, surprise) | 0.80 |
| **corr(inflation metric, growth metric)** | **−0.018** |
| Metric range | −5.61pp (2009Q2) to +6.37pp (2022Q1) |
| Largest upside surprise in the sample | **2022Q1, z = +2.95** |
| Largest downside surprise | 2009Q2, z = −2.72 |

Two consequences. The two macro metrics are **essentially uncorrelated** over the full sample,
which is what makes the two-factor partial correlation well behaved — and also why the growth
control moves the point estimates very little while still raising confidence in them. And
scaling to *change*'s standard deviation rather than to 1 keeps the metric in percentage points,
which is how the deck plots it.

### 3.7 In-sample caveats that apply to the whole study

- **Every regime classification uses a full-sample z-score.** The tritile sort therefore uses
  information from the future. Fine for the descriptive question ("how did assets behave when
  inflation surprised?"); **not** fine for a trading rule.
- **Every weight in the portfolio panel is chosen in-sample.** It is a study of what diversified
  inflation surprises historically, not a backtest of a strategy anyone could have run.
- The 2022–23 episode strengthened every real-asset result, which is reassuring for the thesis
  and also exactly what adding a confirming episode to a 50-year sample does. It is not
  independent evidence of much.

---

## 4. Data sourcing findings

Every data source used, what it costs, and the dead ends found along the way.

### 4.1 Every substitution, and what it costs

| Sleeve | 2022 deck (Bloomberg unless noted) | Here | Cost |
|---|---|---|---|
| US equities | MSCI USA Net TR (`NDDUUS`) | CRSP value-weighted market + RF (Ken French), 1926-07– | all-cap not large/mid; gross of withholding tax; ~1pp more volatile |
| Treasuries 5/10/20y | FRED constant maturity + Swinkels | *unchanged* — but month-end `DGS*`, see §4.3 | none |
| Commodities | S&P GSCI TR (`SPGSCITR`) | AQR equal-weight + T-bill, spliced to `GSG` | equal- not production-weight; AQR's own Exhibit A1c puts the two at 0.66 vs 0.67 inflation sensitivity |
| Gold | Bloomberg Gold Subindex TR (`BCOMGCTR`) | LBMA PM fix + T-bill collateral, 1968-04– | negligible; collateral makes spot comparable to a futures index |
| Precious metals | Bloomberg Precious Metals TR (`BCOMPRTR`) | 80/20 gold/silver + collateral | approximates the subindex's actual composition |
| REITs | FTSE NAREIT All Equity TR (`FNERTR`) | **the same index**, from NAREIT's own workbook | none to the data; the cost is operational (manual download) |
| CPI / core CPI | `CPI INDX` | FRED `CPIAUCNS` / `CPILFENS` | none — same quantity |
| Real GDP | `GDP CYOY` | FRED `GDPC1` | none |
| CPI forecast | Philadelphia Fed SPF | SPF, spliced before 1981Q3 | **the one real assumption** — §3.4 |
| Cash / collateral | n/a | FRED `TB3MS` | discount basis, so marginally understates a bond-equivalent yield |

### 4.2 FRED has *removed* licensed third-party series, not merely truncated them

`GOLDAMGBD228NLBM`, `GOLDPMGBD228NLBM`, `SLVPRUSD`, `WILL5000IND`, `WILLREITIND` all return
**HTTP 400** as of 2026-09-17. This is the ICE BofA three-year truncation one step further
along. **Standing implication for the whole repo: treat any FRED series sourced from a
commercial index provider as on borrowed time, and prefer the primary issuer where one exists.**
That is why gold here comes from LBMA directly — which turns out to be *longer* history than
FRED ever carried (1968-04 daily).

### 4.3 FRED's monthly `GS*` yields are monthly *averages*

Harmless for levels. Silently wrong for anything deriving a **return**: differencing a monthly
average smears each month's yield move across two months. Measured against IEF over 290 months,
same par-bond formula:

| Built on | Correlation with IEF |
|---|---|
| `GS10` (monthly average) | **0.72** |
| `DGS10` sampled at month end | **0.99** |

Anything computing a return from a FRED yield must sample the daily series at month end. (The
app is unaffected — `lib/catalogue.ts` uses `DGS*`, and nothing in `lib/macro/` derives a return
from a yield.)

### 4.4 philadelphiafed.org soft-200s a missing file

A wrong path returns an **HTML page with status 200**, not a 404, so `raise_for_status()` passes
and you cache a web page as `.xlsx`. Guessed filenames are unsafe here. `sources._http_get`
rejects any body starting with `<`.

### 4.5 SPF coverage windows

| Sheet | First observation | Note |
|---|---|---|
| `CPI` | **1981Q3** | the constraint behind §3.4 |
| `CORECPI` | 2007Q1 | too short to be useful here |
| `PGDP` (GDP price index) | **1968Q4** | continuous — the splice source |
| `RGDP` | **1968Q4** | continuous — the growth forecast |

Column *n* of a sheet is the forecast for the survey quarter (n=1) and the following five;
letter columns are annual averages. `PGDP`/`RGDP` are index *levels*, so a 4-quarter forecast is
the ratio of column 5 to column 1. `CPI` columns are annualised quarterly *rates*, so they
compound.

### 4.6 NAREIT: fingerprint-walled, integrated by hand

- **Page**: `reit.com/data-research/reit-market-data/report/monthly-index-values-returns`.
  (An earlier guess at `/data-research/reit-indexes/…` was wrong and is corrected everywhere.)
- **File**: `/sites/default/files/returns/MonthlyHistoricalReturns.xls` — "Monthly Historical
  Index Data: 1972 - 2026", 538KB legacy `.xls`, covering 1971-12 → 2026-08. **Not**
  `MonthlyReturns.xls`, which is the current year only.
- **Every path on the domain is walled, the direct file included** — re-verified 2026-09-18 with
  a browser User-Agent *and* a matching `Referer`: the same 3KB challenge page, status 200. No
  API. `WebFetch` can read the HTML *pages* (that is how the real URLs were recovered) but
  cannot hand over a binary, so the workbook must come from a real browser.
- **Layout**, because a tolerant parser is the wrong instinct — a wrong column would be
  indistinguishable from a real result: sheet `Index Data`; six index families side by side as
  seven-column blocks; header split across three rows (group name, then
  `Total`/`Price`/`Income`, then `Return`/`Index`/`Yield`); dates in column 0; data from row 9.
  **Monthly total return is published directly, in percent** — read it, do not difference the
  index level. `sources.nareit_all_equity_return` locates the group by label, asserts the
  sub-header really says Total Return, and raises on any layout change.
- Sanity figures for the parsed series: 656 months, 1972-01 → 2026-08, 10.96% annualised, 17.1%
  annualised volatility, 293.9× cumulative.

### 4.7 Dead ends and fallbacks

| Target | Verdict |
|---|---|
| **stooq.com** (was a soft route to metals/FX) | now a SHA-256 proof-of-work wall. LBMA is better anyway |
| Yahoo `^SPGSCI` | starts 1985, and is a price index not total return |
| Yahoo `^BCOM` | stale — last monthly bar 2020-10 |
| Yahoo REIT proxies | `^FNER` 2012–, `^RMZ` stops 2021-09, `VNQ` 2004-09– |
| Ken French real-estate industry portfolio | 1926–, but real-estate *equities*, not REITs |
| **World Bank Pink Sheet** | works (765KB, monthly commodity prices from 1960); spot only, no total returns, so unused — but it is the standing fallback if LBMA closes its JSON. Note the widely-linked `18675f1d…` URL 404s; use `5d903e848db1d1b83e0ec8f744e55570-0350012021` |
| Longest ETF history available | **33.7 years** (SPY, 1993) against the study's 55 — the argument for index/academic proxies in one number |

### 4.8 The commodity splice

AQR's file ends **2025-05**; the tail is `GSG`.

| Diagnostic | Value |
|---|---|
| Overlap | 226 months |
| Correlation over the overlap | **0.870** |
| Spliced months | 16 (from 2025-06) |

0.87 is about as close as equal-weight and production-weight get. The splice disappears if a
live equal-weight series turns up.

---

## 5. Errors found in the original deck

### 5.1 The convexity formula (slide 32) is typeset wrong

It prints the final denominator as `[Y·(1+0.5Y)]^(2M+1)` — bracket around the whole product.
Implemented as printed, at Y=5% and M=10 that term is some **twenty orders of magnitude** too
large and the convexity correction swamps the return. The exponent belongs on the compounding
factor alone:

```
C = (2/Y²)·[1 − 1/(1+0.5Y)^(2M)] − (2M)/(Y·(1+0.5Y)^(2M+1))
```

which gives the ~73.6 years² a 10-year par bond at 5% should have. Almost certainly a Word
equation-editor artefact rather than an error in the original code, since the deck's treasury
series looks right — but anyone re-implementing from the PDF would have been bitten.

### 5.2 The slide-28 weights sum to 1.10, not 1.00

60 + 25 + 10 + 15 = 110%. Either the original ran a 110%-gross portfolio or it normalised behind
the scenes. Unknowable from the PDF, so `portfolio.panel_figure` exposes a `normalise` toggle
rather than guessing; §1.2 reports both.

---

## 6. Bugs found and fixed during the build

Recorded because each one is a trap that would recur.

| Bug | Symptom | Cause / fix |
|---|---|---|
| `pandas.PeriodIndex(year=…, quarter=…)` | `TypeError: unexpected keyword argument 'year'` | removed in pandas 3.0; build the index from `f"{y}Q{q}"` strings |
| `.style` on the provenance table | `AttributeError: The '.style' accessor requires jinja2` | it *appeared* to work only because `nbconvert`'s own environment supplies jinja2 — the notebook would have failed in the project venv under VS Code. `jinja2` is now a declared dependency |
| NAREIT parser | `TypeError: argument of type 'float' is not iterable`, the moment a real file appeared | pandas 3.0 returns NA (not the string `"nan"`) from `.astype(str).str.lower()`. Rewritten to assert the known layout rather than sniff for it |
| Treasury reconstruction | 0.72 correlation with IEF where ~0.99 was expected | `GS10` is a monthly average; switched to month-end `DGS10` (§4.3). **Found only because the reconstruction was validated externally** |

---

## 7. Validation performed

| Check | Result |
|---|---|
| Treasury reconstruction vs IEF, 290 months | correlation **0.99**; vol 7.59% vs 6.62% and return 2.87% vs 3.42% — expected, IEF is a 7–10y ladder not a constant-maturity 10y par bond |
| AQR commodities vs GSG, 226 months | correlation 0.870 |
| Sensitivities vs the 2022 deck | every sign matches, magnitudes within ~0.06 (§1.1) |
| Tritiles vs the deck, on the deck's window | converge (§3.5) |
| Chart palette | validated for colourblind separation (OKLab ΔE): 3-series all-pairs CVD 9.2 / normal-vision 24.0; 7-series adjacent CVD 9.1 / 19.6 |
| Test suite | 18 pytest tests, covering the metric algebra, the bond math and the NAREIT parser |
| Notebook | executes end to end with zero errors, 14 figures, ~4s warm |

The palette change also fixed an accessibility problem in the original: the deck shaded regimes
red/green and coloured its tritile bars red/yellow/green — the one distinction ~8% of men cannot
make. Replaced with a validated diverging pair.

---

## 8. Open questions

1. **The portfolio panel's residual gap** (§1.2). Cause is attributed but not decomposed. Could
   be settled by re-running the panel on an S&P 500 total return series instead of CRSP all-cap.
2. **The Livingston Survey** would be a methodologically cleaner pre-1981 fill than the deflator
   splice — semiannual CPI forecasts back to 1946, and a genuine CPI forecast rather than a proxy. Not
   pursued because Philly Fed's file paths could not be found and guessing is unsafe (§4.4).
   Would need the real filenames, then interpolation to quarterly.
3. **Whether the deck's regime dating matched ours.** Its metric used its own forecast series, so
   the upside/downside quarter sets may differ slightly. Not checkable from the PDF.
4. **Was the deck's REIT sleeve really `FNERTR`?** Its tritile figures (4.4/3.2/5.6) sit above
   ours even on its own window (3.20/3.64/3.75). The sensitivities match closely, so the series
   is probably right and the difference is regime dating (2 above).
5. **A commodity series that does not need splicing** (§4.8).

## 9. Built since the first pass (2026-09-18)

### 9.1 Time-varying correlations — the stability claim only half holds

Rolling 10-year (40-quarter) correlation of YoY returns with the combined inflation metric,
simple (not growth-controlled), windows ending 1981Q4 onward:

| Sleeve | Full sample | Lowest 10y | Highest 10y | Windows with full-sample sign |
|---|---|---|---|---|
| UST 10y | −0.46 | −0.79 | −0.08 | **100%** |
| Commodities | +0.63 | +0.39 | +0.84 | **100%** |
| Gold | +0.48 | −0.35 | +0.81 | 85% |
| Precious metals | +0.48 | −0.35 | +0.80 | 84% |
| 60/40 | −0.33 | −0.75 | +0.66 | 69% |
| US equities | −0.19 | −0.66 | +0.66 | **61%** |
| REITs | −0.02 | −0.78 | +0.66 | 60% |

The two sleeves the conclusions rest on hardest — treasuries and commodities — never change sign.
**Equities do**: clearly negative through the 1980s–90s, around +0.4 through most of the 2010s,
near zero in the latest decade. The full-sample equity sensitivity is an average over regimes, not
a steady property — consistent with inflation news reading as bad news when inflation is high and
as reflation when it is low. **Gold turned negative (≈ −0.33) in the latest decade**: flat through
the 2022 surprise, then a large rally as inflation news faded. The 2022 deck's slide 34 read the
scatter as showing no drift; the rolling figures say that holds for bonds and commodities only.

### 9.2 Backtest-only sleeves and horizons

`dataset.backtest_universe` adds sleeves used only by the Part 5 app and the correlation charts:

| Sleeve | Source | Usable from |
|---|---|---|
| UST 5y / 20y | FRED `DGS5` / `DGS20`, month-end | 1962 / **1993-10** (20y gap 1987-01 → 1993-09) |
| IG credit, modelled | Moody's Baa as a 30y par bond: `BAA` monthly averages to 1985, month-end `DBAA` from 1986 | 1919 |
| IG fund | VWESX | 1985-02 |
| HY fund | VWEHX | 1985-02 |
| EM debt fund | FNMIX | 1993-06 |
| Govt bond fund | FGOVX (Treasuries + agencies + agency MBS; the user's choice over pure-Treasury GOVT, 2012–) | 1985-02 |
| TIPS fund | VIPSX | 2000-07 |
| GSCI fund | GSG | 2006-08 |

Horizons: full sample (1972–, 9 sleeves including cash, 25 upside / 25 downside quarters), since
1986 (12 sleeves, 11 / 12), since 2007 (16 sleeves, 11 / 8). **Almost every post-1986 upside surprise is post-2007**,
so the two short horizons share nearly the same inflation evidence.

Sourcing dead ends established while building it: FRED's ICE BofA credit total-return indices
(`BAMLCC0A0CMTRIV`, `BAMLHYH0A0HYM2TRIV`) now serve only 3 years; Yahoo's mutual-fund monthly
history is capped at 1985-02 however old the fund; FRED's TIPS real yields (`DFII5/10`) start 2003.

Validation: the modelled IG sleeve against VWESX over 500 months correlates **0.92**, vol 10.8% vs
9.0% — expected for a longer-duration model with no fund fees or default drag.

### 9.3 Backtest statistics and the Sharpe convention

The app's statistics table compares the portfolio with US equities, UST 10y and the 60/40 over
exactly the portfolio's months: annualised return and volatility, Sharpe and Sortino, max drawdown,
max 12-month drawdown (worst peak-to-trough inside any 12-month window), worst and best 12-month
return, longest drawdown, Calmar, share of positive months, and both partial correlations.

**Sharpe and Sortino are measured against the realised one-month T-bill return** (Ken French `RF`,
the cash sleeve), month by month — not the fixed 1.5% used in §1.2's comparison with the 2022
deck. The two answer different questions: the fixed rate reproduces the deck's number; the realised
rate is the standard definition. For the 60/25/10/15 portfolio, 1972-01 → 2026-07: Sharpe **0.96**
at a fixed 1.5%, **0.67** against T-bills, which averaged 4.4% a year over the period.

Drawdowns are measured from a starting value of 1, so a loss in the first month counts.

### 9.4 Still not built

Equity-style and sector drill-downs (value/growth from Ken French's 6 portfolios, 1926–);
out-of-sample regime classification; an unspliced commodity series. Listed in the notebook's
Appendix C.

## 10. Reproducing this

```bash
cd python/inflation-surprises
uv sync
uv run pytest                 # 18 tests
uv run jupyter lab            # or select .venv as the kernel in VS Code
```

Needs `FRED_API_KEY` in the repo's `.env.local`; everything else is unauthenticated. First run
downloads ~2MB into `cache/` (delete it to force a refresh). The REIT sleeve additionally needs
the manual NAREIT workbook in `manual/` (§4.6) — without it the sleeve drops out and the
notebook says so.

## References

1. **Thapar, A., T. Maloney and A. Brixton (2021)**, "When Stock-Bond Diversification Fails:
   Managing inflation risk in investor portfolios", AQR Capital Management, October 2021. The
   source of the change/surprise/combined metric, the tritile sort and the two-factor partial
   correlation framing.
2. **Lau, S. and A. Botte (2022)**, "A Machine Learning Approach to Constructing an
   Inflation-Themed Equity Portfolio", Two Sigma Street View, 26 January 2022. The source of the
   inflation-*level* bucketing (high >3% / medium 1–3% / low <1%) that the study discusses and
   rejects in favour of surprises, and of the sector/style drill-down idea.
3. **Swinkels, L. (2019)**, "Treasury bond return data starting in 1962", *Data in Brief* 24.
   The par-bond reconstruction.
4. **Levine, A., Y. H. Ooi, M. Richardson and C. Sasseville (2018)**, "Commodities for the Long
   Run", *Financial Analysts Journal* 74(2). The commodity series, via AQR's public data library.
