"""Treasury total returns reconstructed from constant-maturity yields.

Method: Swinkels, Laurens (2019), "Treasury bond return data starting in 1962",
*Data in Brief* 24. A constant-maturity par bond is assumed, so each month's
return is the yield accrued over the month plus the price change implied by the
yield move, taken to second order in duration and convexity.

One correction to the original deck's appendix (slide 32): its convexity
formula prints the final denominator as ``[Y*(1+0.5Y)]^(2M+1)`` — the bracket
placed around the whole product. That cannot be right; at Y=5%, M=10 it returns
a number ~10^20 too large and the convexity term swamps the return. Swinkels'
formula puts the exponent on the compounding factor alone,
``Y*(1+0.5Y)^(2M+1)``, which gives the ~74 years² a 10-year par bond should
have. We use the latter.
"""

from __future__ import annotations

import pandas as pd


def modified_duration(ytm: pd.Series | float, maturity: float) -> pd.Series | float:
    """Modified duration of a par bond, semi-annual coupons. ``ytm`` in decimals."""
    return (1.0 / ytm) * (1.0 - 1.0 / (1.0 + 0.5 * ytm) ** (2.0 * maturity))


def convexity(ytm: pd.Series | float, maturity: float) -> pd.Series | float:
    """Convexity of a par bond, semi-annual coupons. ``ytm`` in decimals."""
    first = (2.0 / ytm**2) * (1.0 - 1.0 / (1.0 + 0.5 * ytm) ** (2.0 * maturity))
    second = (2.0 * maturity) / (ytm * (1.0 + 0.5 * ytm) ** (2.0 * maturity + 1.0))
    return first - second


def par_bond_monthly_returns(yields_percent: pd.Series, maturity: float) -> pd.Series:
    """Monthly total return of a constant-maturity par bond.

    Parameters
    ----------
    yields_percent
        Monthly constant-maturity yield in percent (e.g. FRED ``GS10``).
    maturity
        Constant maturity in years.

    Returns
    -------
    Monthly total return in decimals, first month NaN.
    """
    ytm = yields_percent.astype(float) / 100.0
    previous = ytm.shift(1)
    change = ytm - previous
    duration = modified_duration(previous, maturity)
    curvature = convexity(previous, maturity)
    return previous / 12.0 - duration * change + 0.5 * curvature * change**2
