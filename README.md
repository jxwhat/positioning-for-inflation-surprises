# Positioning for Inflation Surprises

A recreation of a 9 March 2022 investment-meeting study of the same name, rebuilt on
public data after the original notebook was lost. The deliverable is
[`positioning-for-inflation-surprises.ipynb`](positioning-for-inflation-surprises.ipynb); it is
committed with its outputs, so it reads on GitHub without being run.

## Running it

```bash
uv sync
uv run jupyter lab              # or pick .venv as the kernel in VS Code
```

The notebook is set to this project's own kernel, **Python (inflation-surprises)**. Register it
once after `uv sync`, or simply pick `.venv` as the kernel in VS Code:

```bash
uv run python -m ipykernel install --user --name inflation-surprises --display-name "Python (inflation-surprises)"
```

Needs `FRED_API_KEY` in the repo's `.env.local` — the loader reads it directly, no shell export
required. Everything else is unauthenticated.

First run downloads roughly 2MB and caches it under `cache/`; later runs are offline except for
the Yahoo calls. Delete `cache/` to force a refresh.

## Charts and exporting

Charts are Plotly: interactive in Jupyter and VS Code, and every output also embeds a PNG so the
committed notebook still shows its charts on GitHub. For a shareable page with interactive
charts, run `uv run python export_html.py --no-code` — a plain `nbconvert --to html` would only
show the PNGs. PNG export uses kaleido, which drives the locally installed Chrome.

Seven exhibits are committed as PNG only — the ones drawing the REIT and commodity sleeves.
Plotly stores a chart's series as decodable arrays, and those two series derive from data that
is licensed to the downloader rather than to this repo, so the interactive layer is stripped
before committing. Re-run the notebook with your own NAREIT workbook in `manual/` and they come
back interactive locally.

## Completed periods only

Loaders keep **completed periods only**: an observation dated in the month its source was fetched
is dropped, so a mid-month "month end" never passes as a whole month.

## The one manual step

The REIT sleeve needs a file that cannot be fetched — reit.com sits behind a JavaScript
fingerprint wall:

1. open <https://www.reit.com/data-research/reit-market-data/report/monthly-index-values-returns>
2. download **"Monthly Historical Index Data: 1972 - 2026"**
   (`https://www.reit.com/sites/default/files/returns/MonthlyHistoricalReturns.xls`) — not "Monthly Index Data: 2026", which covers the current year only
3. drop it in `manual/` with `nareit` somewhere in the filename

Until then the notebook runs without REITs and says so. `manual/` is gitignored — the data is
licensed to whoever downloads it, not to this repo.

## Licence

The code and write-up in this repository are MIT licensed (see `LICENSE`). That covers this
work only — not the upstream data. FRED, Yahoo, AQR, NAREIT and the cited papers each carry
their own terms, and nothing here relicenses them.

## Module map

| File | Holds |
|---|---|
| `sources.py` | one loader per upstream source, plus `SOURCE_MAP` (the provenance table the notebook renders) |
| `dataset.py` | assembly and every judgement call: the pre-1981 forecast splice, the commodity splice, collateral legs |
| `metrics.py` | the change / surprise / combined construction, regime classification, partial correlations, Newey-West inference |
| `bondmath.py` | Swinkels (2019) par-bond total returns from constant-maturity yields |
| `charts.py` | the recurring exhibit shapes (Plotly, terminal theme) and the validated palette |
| `export_html.py` | writes a standalone HTML page with interactive charts (`--no-code` hides code cells) |
| `portfolio.py` | the backtest: horizons, sleeve availability and the static exhibit |
| `episodes.py` | shock episodes — contiguous runs of quarters `metrics.classify` calls a shock, and what each portfolio did inside them |
| `test_core.py` | `uv run pytest` — covers the metric algebra and the bond math |

The notebook holds the narrative and the one-off exhibits; the modules hold anything used more
than once or worth testing.

## Known gaps

Ideas for further work are listed in the notebook's Appendix C. The backtest-only sleeves (credit,
government and TIPS funds, GSCI fund) only reach back to 1985–2006, which is why the Part 5 app
offers three horizons; FINDINGS.md §9.2 has each start date. The commodity series is AQR's
equal-weight index through May 2025 and GSG thereafter — a splice that disappears if a live
equal-weight series turns up.

The REIT sleeve is live but not self-updating: it reads whatever NAREIT workbook is sitting in
`manual/`, so it goes stale until that file is downloaded again. `sources.nareit_all_equity_return`
raises rather than guessing if NAREIT changes the layout, and returns `None` — dropping the
sleeve — if the file is missing entirely.
