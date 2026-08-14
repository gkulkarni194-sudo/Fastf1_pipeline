import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS


def create_timeline(start_date="2016-01-01", end_date="2026-05-01"):
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    return pd.DataFrame(index=dates), dates


def generate_synthetic_asset_pricing_data(df, dates):
    df["WML_gross"] = np.random.normal(loc=0.0008, scale=0.012, size=len(dates))
    df["MKT_excess"] = np.random.normal(loc=0.0005, scale=0.01, size=len(dates))
    return df


def apply_tax_shock_dummy(df, tax_shock_dates):
    df["Tax_Shock_Dummy"] = 0

    for date_str in tax_shock_dates:
        event_date = pd.to_datetime(date_str)
        window = pd.date_range(
            end=event_date + pd.Timedelta(days=15), periods=30, freq="D"
        )
        df.loc[df.index.isin(window), "Tax_Shock_Dummy"] = 1

    return df


def apply_rbi_hawkish_dummy(df, dates):
    df["RBI_Hawkish_Dummy"] = np.where(
        np.random.uniform(0, 1, len(dates)) > 0.7, 1, 0
    )
    return df


def apply_structural_breaks_and_policy_lags(df, dates):
    tax_shock_dates = [
        "2018-02-01",
        "2024-07-23",
        "2026-04-01",
    ]

    df = apply_tax_shock_dummy(df, tax_shock_dates)
    df = apply_rbi_hawkish_dummy(df, dates)
    return df


def calculate_net_returns(df):
    df["Transaction_Cost"] = 0.0002
    df.loc[df["Tax_Shock_Dummy"] == 1, "Transaction_Cost"] = 0.0006
    df["WML_net"] = df["WML_gross"] - df["Transaction_Cost"]
    return df


def run_conditional_regression(df):
    x = df[["MKT_excess", "Tax_Shock_Dummy", "RBI_Hawkish_Dummy"]]
    x = sm.add_constant(x)
    y = df["WML_net"]

    return OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": 15})


def build_dataset():
    np.random.seed(42)

    df, dates = create_timeline()
    df = generate_synthetic_asset_pricing_data(df, dates)
    df = apply_structural_breaks_and_policy_lags(df, dates)
    df = calculate_net_returns(df)
    return df


def main():
    df = build_dataset()
    model = run_conditional_regression(df)
    print(model.summary())


if __name__ == "__main__":
    main()
