from pathlib import Path

import pandas as pd


DATA_DIR = Path("data/generated")


def load_entities() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "entities.csv")


def load_accounts() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "accounts.csv")


def load_transactions() -> pd.DataFrame:
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"]
    )
    return transactions
