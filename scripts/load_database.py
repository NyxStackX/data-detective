from pathlib import Path

import pandas as pd
import psycopg


DATA_DIR = Path("data/generated")

DATABASE_URL = (
    "postgresql://detective:detective@localhost:5433/data_detective"
)


def clean_dataframe(df):
    return df.astype(object).where(pd.notna(df), None)


def load_entities(connection):
    df = pd.read_csv(DATA_DIR / "entities.csv")
    df = clean_dataframe(df)

    with connection.cursor() as cursor:
        for row in df.itertuples(index=False):
            cursor.execute(
                """
                INSERT INTO entities (
                    entity_id,
                    entity_name,
                    entity_type,
                    parent_entity_id,
                    country,
                    city,
                    industry,
                    creation_date,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                ON CONFLICT (entity_id) DO NOTHING
                """,
                tuple(row),
            )

    connection.commit()
    print(f"Entities loaded: {len(df)}")


def load_accounts(connection):
    df = pd.read_csv(
        DATA_DIR / "accounts.csv",
        parse_dates=["opening_date", "closing_date"],
    )
    df = clean_dataframe(df)

    with connection.cursor() as cursor:
        for row in df.itertuples(index=False):
            cursor.execute(
                """
                INSERT INTO accounts (
                    account_id,
                    entity_id,
                    bank_name,
                    country,
                    city,
                    currency,
                    account_type,
                    opening_date,
                    closing_date,
                    status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (account_id) DO NOTHING
                """,
                tuple(row),
            )

    connection.commit()
    print(f"Accounts loaded: {len(df)}")


def load_transactions(connection):
    df = pd.read_csv(
        DATA_DIR / "transactions.csv",
        parse_dates=["transaction_date"],
    )
    df = clean_dataframe(df)

    columns = [
        "transaction_id",
        "transaction_date",
        "source_account_id",
        "destination_account_id",
        "source_entity_id",
        "destination_entity_id",
        "amount",
        "currency",
        "amount_eur",
        "transaction_type",
        "reference",
        "description",
        "status",
        "authorized_by",
        "created_by",
    ]

    with connection.cursor() as cursor:
        for row in df[columns].itertuples(index=False):
            cursor.execute(
                """
                INSERT INTO transactions (
                    transaction_id,
                    transaction_date,
                    source_account_id,
                    destination_account_id,
                    source_entity_id,
                    destination_entity_id,
                    amount,
                    currency,
                    amount_eur,
                    transaction_type,
                    reference,
                    description,
                    status,
                    authorized_by,
                    created_by
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (transaction_id) DO NOTHING
                """,
                tuple(row),
            )

    connection.commit()
    print(f"Transactions loaded: {len(df)}")


def main():
    with psycopg.connect(DATABASE_URL) as connection:
        load_entities(connection)
        load_accounts(connection)
        load_transactions(connection)

    print("Database loading completed successfully.")


if __name__ == "__main__":
    main()
