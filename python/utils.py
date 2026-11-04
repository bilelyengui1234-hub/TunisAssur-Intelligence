"""
utils.py — small shared helpers for the generators.

Key idea: each generator gets its OWN seeded random stream via get_rng(offset).
Independent substreams mean re-running one generator never shifts another's output,
yet everything stays reproducible from the single SEED in config.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


def get_rng(offset: int = 0) -> np.random.Generator:
    """Return a reproducible NumPy random Generator for a given generator offset."""
    return np.random.default_rng(config.SEED + offset)


def weighted_choice(rng: np.random.Generator, values, weights, size: int):
    """Draw `size` items from `values` with probabilities `weights` (auto-normalized)."""
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    idx = rng.choice(len(values), size=size, p=w)
    arr = np.asarray(values, dtype=object)
    return arr[idx]


def random_dates(rng: np.random.Generator, start, end, size: int) -> pd.DatetimeIndex:
    """Uniform random dates (day resolution) in [start, end] inclusive."""
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    span_days = (end - start).days
    offs = rng.integers(0, span_days + 1, size=size)
    return pd.to_datetime(start) + pd.to_timedelta(offs, unit="D")


def random_dates_between(rng: np.random.Generator, starts: pd.Series, ends: pd.Series) -> pd.Series:
    """
    Per-row uniform random date in [starts_i, ends_i]. Vectorized.
    Used where each row has its own valid window (e.g. registration after 18th birthday).
    """
    starts = pd.to_datetime(starts)
    ends = pd.to_datetime(ends)
    span = (ends - starts).dt.days.clip(lower=0).to_numpy()
    offs = (rng.random(len(span)) * (span + 1)).astype(int)
    offs = np.minimum(offs, span)  # keep within [0, span]
    return starts + pd.to_timedelta(offs, unit="D")


def pk_is_unique(df: pd.DataFrame, col: str) -> bool:
    return df[col].is_unique and df[col].notna().all()
