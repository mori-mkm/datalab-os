"""Synthetic churn-like sample data, only so the PoC runs out of the box. Regenerate with:

    python -m datalab.tools.sample_data
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from datalab.config import ROOT


def make_sample(n: int = 1200, seed: int = 7, leak: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tenure = rng.integers(1, 73, n)
    monthly = rng.normal(70, 25, n).clip(15, 150).round(2)
    tickets = rng.poisson(1.5, n)
    contract = rng.choice(["month-to-month", "one-year", "two-year"], n, p=[0.55, 0.25, 0.20])
    payment = rng.choice(["card", "bank_transfer", "electronic_check", "mail"], n)
    logit = (
        -0.8
        - 0.04 * tenure
        + 0.015 * (monthly - 70)
        + 0.35 * tickets
        + np.select([contract == "month-to-month", contract == "one-year"], [1.0, 0.0], default=-1.0)
    )
    churned = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    df = pd.DataFrame(
        {
            "customer_id": [f"C{i:05d}" for i in range(n)],
            "tenure_months": tenure,
            "monthly_charges": monthly,
            "support_tickets": tickets,
            "contract": contract,
            "payment_method": payment,
            "churned": churned,
        }
    )
    df.loc[rng.random(n) < 0.04, "monthly_charges"] = np.nan
    df.loc[rng.random(n) < 0.03, "payment_method"] = np.nan
    if leak:  # not declared anywhere: the reviewer has to catch it
        df["account_closed_flag"] = churned
    return pd.concat([df, df.sample(5, random_state=seed)], ignore_index=True)  # a few duplicate rows


if __name__ == "__main__":
    out = ROOT / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    make_sample().to_csv(out / "sample_churn.csv", index=False)
    make_sample(leak=True).to_csv(out / "sample_churn_leaky.csv", index=False)
    make_sample(n=200, seed=99).to_csv(out / "sample_small.csv", index=False)  # small dataset for fast end-to-end checks
    print(f"wrote {out / 'sample_churn.csv'}, {out / 'sample_churn_leaky.csv'} and {out / 'sample_small.csv'}")
