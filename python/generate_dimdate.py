"""
generate_dimdate.py — DimDate (a professional date dimension).

Grain: one row = one calendar day, 2022-01-01 .. 2025-12-31.
A dedicated date table is mandatory for correct time-intelligence in Power BI
(YTD, YoY, MoM). We generate it in Python (reproducible, French labels, sort keys)
rather than a volatile in-model CALENDAR() so it can also live in SQL if needed.

Key design:
  - DateKey : integer yyyymmdd (fast joins, clean sort; facts can store this).
  - French month/day names (business language) WITH numeric sort columns so visuals
    order chronologically, not alphabetically.
  - ISO week number; weekend flag.

Output: data/cleaned/dimdate.csv
"""
from __future__ import annotations

import pandas as pd

import config

MONTHS_FR = {1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
             7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"}
MONTHS_FR_SHORT = {1: "Janv", 2: "Févr", 3: "Mars", 4: "Avr", 5: "Mai", 6: "Juin",
                   7: "Juil", 8: "Août", 9: "Sept", 10: "Oct", 11: "Nov", 12: "Déc"}
DAYS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}


def generate() -> pd.DataFrame:
    dates = pd.date_range(config.START_DATE, config.END_DATE, freq="D")
    df = pd.DataFrame({"Date": dates})
    d = df["Date"].dt

    df["DateKey"] = (d.year * 10000 + d.month * 100 + d.day).astype(int)
    df["Year"] = d.year
    df["Quarter"] = d.quarter
    df["QuarterName"] = "T" + d.quarter.astype(str)
    df["YearQuarter"] = d.year.astype(str) + "-T" + d.quarter.astype(str)
    df["MonthNumber"] = d.month
    df["MonthName"] = d.month.map(MONTHS_FR)
    df["MonthShort"] = d.month.map(MONTHS_FR_SHORT)
    df["YearMonth"] = d.strftime("%Y-%m")
    df["YearMonthSort"] = (d.year * 100 + d.month).astype(int)
    df["MonthYearLabel"] = d.month.map(MONTHS_FR_SHORT) + " " + d.year.astype(str)
    df["WeekOfYear"] = d.isocalendar().week.astype(int)
    df["DayOfMonth"] = d.day
    df["DayOfWeek"] = d.weekday + 1                       # Monday = 1 .. Sunday = 7
    df["DayName"] = d.weekday.map(DAYS_FR)
    df["IsWeekend"] = d.weekday.isin([5, 6]).astype(int)

    # normalize Date to date (no time)
    df["Date"] = df["Date"].dt.normalize()
    return df


def validate(df: pd.DataFrame) -> None:
    assert df["DateKey"].is_unique, "DateKey must be unique"
    assert df["Date"].is_unique, "Date must be unique"
    assert len(df) == (pd.Timestamp(config.END_DATE) - pd.Timestamp(config.START_DATE)).days + 1
    assert df["Date"].min() == pd.Timestamp(config.START_DATE)
    assert df["Date"].max() == pd.Timestamp(config.END_DATE)
    # every day present, no gaps
    assert (df["Date"].diff().dropna() == pd.Timedelta(days=1)).all(), "gap in calendar"


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "dimdate.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_dimdate: wrote {len(df)} days -> {out}")
    print(f"Range: {df['Date'].min().date()} .. {df['Date'].max().date()} "
          f"({df['Year'].nunique()} years, {df['YearMonth'].nunique()} months)")
    print("\nColumns:", ", ".join(df.columns))
    print("\nSample:")
    print(df.head(4).to_string(index=False))
    print(df.tail(2).to_string(index=False))


if __name__ == "__main__":
    main()
