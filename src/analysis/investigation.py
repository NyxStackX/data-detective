from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "generated"


def load_data():
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    entities = pd.read_csv(DATA_DIR / "entities.csv")

    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"]
    )

    return transactions, accounts, entities


def build_transaction_view(transactions, accounts, entities):
    account_entity = accounts[
        ["account_id", "entity_id"]
    ].copy()

    entity_info = entities[
        [
            "entity_id",
            "entity_name",
            "entity_type",
            "country",
        ]
    ].copy()

    data = transactions.merge(
        account_entity.rename(
            columns={"entity_id": "source_entity"}
        ),
        left_on="source_account_id",
        right_on="account_id",
        how="left",
    ).drop(columns=["account_id"])

    data = data.merge(
        account_entity.rename(
            columns={"entity_id": "destination_entity"}
        ),
        left_on="destination_account_id",
        right_on="account_id",
        how="left",
    ).drop(columns=["account_id"])

    source_info = entity_info.rename(
        columns={
            "entity_id": "source_entity",
            "entity_name": "source_entity_name",
            "entity_type": "source_entity_type",
            "country": "source_country",
        }
    )

    destination_info = entity_info.rename(
        columns={
            "entity_id": "destination_entity",
            "entity_name": "destination_entity_name",
            "entity_type": "destination_entity_type",
            "country": "destination_country",
        }
    )

    data = data.merge(
        source_info,
        on="source_entity",
        how="left",
    )

    data = data.merge(
        destination_info,
        on="destination_entity",
        how="left",
    )

    return data


def calculate_entity_flows(data):
    outgoing = (
        data.groupby("source_entity")["amount"]
        .sum()
        .rename("outgoing_amount")
    )

    incoming = (
        data.groupby("destination_entity")["amount"]
        .sum()
        .rename("incoming_amount")
    )

    outgoing_count = (
        data.groupby("source_entity")
        .size()
        .rename("outgoing_count")
    )

    incoming_count = (
        data.groupby("destination_entity")
        .size()
        .rename("incoming_count")
    )

    flows = pd.concat(
        [
            incoming,
            outgoing,
            incoming_count,
            outgoing_count,
        ],
        axis=1,
    ).fillna(0)

    flows["net_flow"] = (
        flows["incoming_amount"]
        - flows["outgoing_amount"]
    )

    flows["flow_ratio"] = (
        flows["outgoing_amount"]
        / flows["incoming_amount"].replace(0, pd.NA)
    )

    return flows.reset_index().rename(
        columns={"index": "entity_id"}
    )


def calculate_counterparty_concentration(data):
    outgoing = (
        data.groupby(
            [
                "source_entity",
                "destination_entity",
            ]
        )["amount"]
        .sum()
        .reset_index()
    )

    total_outgoing = (
        outgoing.groupby("source_entity")["amount"]
        .sum()
        .rename("total_outgoing")
    )

    outgoing = outgoing.merge(
        total_outgoing,
        on="source_entity",
        how="left",
    )

    outgoing["share"] = (
        outgoing["amount"]
        / outgoing["total_outgoing"]
    )

    return (
        outgoing.groupby("source_entity")["share"]
        .max()
        .rename("max_counterparty_share")
        .reset_index()
    )


def calculate_large_transactions(data):
    large = data[
        data["amount"] >= 900_000
    ]

    return (
        large.groupby("source_entity")
        .size()
        .rename("large_transaction_count")
        .reset_index()
    )


def calculate_repeated_transfers(data):
    transfers = data[
        data["transaction_type"].isin(
            [
                "transfer",
                "internal_transfer",
            ]
        )
    ]

    return (
        transfers.groupby("source_entity")
        .size()
        .rename("transfer_count")
        .reset_index()
    )


def generate_investigation_report(data):
    flows = calculate_entity_flows(data)
    concentration = calculate_counterparty_concentration(data)
    large_transactions = calculate_large_transactions(data)
    repeated_transfers = calculate_repeated_transfers(data)

    scores = flows.merge(
        concentration,
        left_on="entity_id",
        right_on="source_entity",
        how="left",
    ).drop(columns=["source_entity"])

    scores = scores.merge(
        large_transactions,
        left_on="entity_id",
        right_on="source_entity",
        how="left",
    ).drop(columns=["source_entity"])

    scores = scores.merge(
        repeated_transfers,
        left_on="entity_id",
        right_on="source_entity",
        how="left",
    ).drop(columns=["source_entity"])

    scores = scores.fillna(0)

    scores["risk_score"] = 0

    scores.loc[
        (
            (scores["incoming_amount"] > 1_000_000)
            & (scores["outgoing_amount"] > 1_000_000)
            & (scores["flow_ratio"] > 1)
        ),
        "risk_score",
    ] += 20

    scores.loc[
        scores["max_counterparty_share"] >= 0.75,
        "risk_score",
    ] += 25

    scores.loc[
        (
            (scores["max_counterparty_share"] >= 0.50)
            & (scores["max_counterparty_share"] < 0.75)
        ),
        "risk_score",
    ] += 15

    scores.loc[
        scores["transfer_count"] >= 10,
        "risk_score",
    ] += 15

    scores.loc[
        scores["large_transaction_count"] >= 5,
        "risk_score",
    ] += 15

    scores["risk_level"] = "LOW"

    scores.loc[
        scores["risk_score"] >= 30,
        "risk_level",
    ] = "MEDIUM"

    scores.loc[
        scores["risk_score"] >= 50,
        "risk_level",
    ] = "HIGH"

    scores.loc[
        scores["risk_score"] >= 70,
        "risk_level",
    ] = "CRITICAL"

    entity_names = data[
        [
            "source_entity",
            "source_entity_name",
            "source_entity_type",
        ]
    ].drop_duplicates()

    scores = scores.merge(
        entity_names,
        left_on="entity_id",
        right_on="source_entity",
        how="left",
    ).drop(columns=["source_entity"])

    return scores.sort_values(
        "risk_score",
        ascending=False,
    )


def detect_circuits(data):
    completed = data[
        data["status"].eq("completed")
    ].copy()

    completed = completed[
        completed["source_entity"]
        != completed["destination_entity"]
    ]

    completed["date"] = (
        completed["transaction_date"]
        .dt.normalize()
    )

    incoming = (
        completed.groupby(
            [
                "destination_entity",
                "source_entity",
                "date",
            ]
        )
        .agg(
            incoming_amount=("amount", "sum"),
            incoming_count=("transaction_id", "count"),
        )
        .reset_index()
        .rename(
            columns={
                "destination_entity": "middle_entity",
                "source_entity": "first_entity",
                "date": "date_in",
            }
        )
    )

    outgoing = (
        completed.groupby(
            [
                "source_entity",
                "destination_entity",
                "date",
            ]
        )
        .agg(
            outgoing_amount=("amount", "sum"),
            outgoing_count=("transaction_id", "count"),
        )
        .reset_index()
        .rename(
            columns={
                "source_entity": "middle_entity",
                "destination_entity": "last_entity",
                "date": "date_out",
            }
        )
    )

    circuits = []

    for middle_entity in incoming[
        "middle_entity"
    ].unique():

        incoming_group = incoming[
            incoming["middle_entity"]
            == middle_entity
        ].sort_values("date_in")

        outgoing_group = outgoing[
            outgoing["middle_entity"]
            == middle_entity
        ].sort_values("date_out")

        if incoming_group.empty or outgoing_group.empty:
            continue

        matches = pd.merge_asof(
            incoming_group,
            outgoing_group,
            left_on="date_in",
            right_on="date_out",
            direction="forward",
            tolerance=pd.Timedelta(days=14),
        )

        matches = matches.dropna(
            subset=["last_entity"]
        )

        matches = matches[
            matches["first_entity"]
            != matches["last_entity"]
        ]

        if matches.empty:
            continue

        matches["amount_ratio"] = (
            matches["outgoing_amount"]
            / matches["incoming_amount"]
        )

        matches["amount_difference"] = (
            (
                matches["outgoing_amount"]
                - matches["incoming_amount"]
            ).abs()
            / matches["incoming_amount"]
        )

        matches = matches[
            (
                matches["incoming_amount"]
                >= 250_000
            )
            & (
                matches["outgoing_amount"]
                >= 250_000
            )
            & (
                matches["amount_difference"]
                <= 0.20
            )
        ]

        for _, row in matches.iterrows():

            if row["amount_difference"] <= 0.05:
                suspicion = "HIGH"
            elif row["amount_difference"] <= 0.10:
                suspicion = "MEDIUM"
            else:
                suspicion = "LOW"

            circuits.append(
                {
                    "first_entity": row[
                        "first_entity"
                    ],
                    "middle_entity": row[
                        "middle_entity"
                    ],
                    "last_entity": row[
                        "last_entity"
                    ],
                    "date_in": row["date_in"],
                    "date_out": row["date_out"],
                    "incoming_amount": row[
                        "incoming_amount"
                    ],
                    "outgoing_amount": row[
                        "outgoing_amount"
                    ],
                    "amount_difference": row[
                        "amount_difference"
                    ],
                    "incoming_count": row[
                        "incoming_count"
                    ],
                    "outgoing_count": row[
                        "outgoing_count"
                    ],
                    "suspicion": suspicion,
                }
            )

    if not circuits:
        return pd.DataFrame()

    result = pd.DataFrame(circuits)

    return result.sort_values(
        [
            "suspicion",
            "incoming_amount",
        ],
        ascending=[True, False],
    )


def enrich_circuits(circuits, entities):
    if circuits.empty:
        return circuits

    names = entities[
        [
            "entity_id",
            "entity_name",
            "entity_type",
        ]
    ].copy()

    for column, prefix in [
        ("first_entity", "first"),
        ("middle_entity", "middle"),
        ("last_entity", "last"),
    ]:
        lookup = names.rename(
            columns={
                "entity_id": column,
                "entity_name": f"{prefix}_name",
                "entity_type": f"{prefix}_type",
            }
        )

        circuits = circuits.merge(
            lookup,
            on=column,
            how="left",
        )

    return circuits


def print_report(scores):
    print()
    print("=" * 80)
    print("DATA DETECTIVE — AUTOMATED INVESTIGATION")
    print("=" * 80)

    print()
    print("TOP INVESTIGATION LEADS")
    print("-" * 80)

    columns = [
        "source_entity_name",
        "source_entity_type",
        "risk_score",
        "risk_level",
        "incoming_amount",
        "outgoing_amount",
        "flow_ratio",
        "max_counterparty_share",
    ]

    display = scores[columns].head(30).copy()

    display["incoming_amount"] = display[
        "incoming_amount"
    ].map(lambda x: f"{x:,.2f}")

    display["outgoing_amount"] = display[
        "outgoing_amount"
    ].map(lambda x: f"{x:,.2f}")

    display["flow_ratio"] = display[
        "flow_ratio"
    ].map(
        lambda x: (
            f"{x:.2f}"
            if pd.notna(x)
            else "N/A"
        )
    )

    display["max_counterparty_share"] = (
        display["max_counterparty_share"]
        .map(lambda x: f"{x:.1%}")
    )

    print(display.to_string(index=False))

    print()
    print("RISK SUMMARY")
    print("-" * 80)

    summary = (
        scores["risk_level"]
        .value_counts()
        .reindex(
            [
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            ],
            fill_value=0,
        )
    )

    for level, count in summary.items():
        print(f"{level:<10} {count}")


def detect_circuits(data):
    completed = data[data["status"].eq("completed")].copy()

    completed = completed[
        completed["source_entity"] != completed["destination_entity"]
    ].copy()

    completed["date"] = completed["transaction_date"].dt.normalize()

    incoming = (
        completed.groupby(
            ["destination_entity", "source_entity", "date"],
            as_index=False
        )
        .agg(
            incoming_amount=("amount", "sum"),
            incoming_count=("transaction_id", "count"),
        )
        .rename(
            columns={
                "destination_entity": "middle_entity",
                "source_entity": "first_entity",
                "date": "date_in",
            }
        )
    )

    outgoing = (
        completed.groupby(
            ["source_entity", "destination_entity", "date"],
            as_index=False
        )
        .agg(
            outgoing_amount=("amount", "sum"),
            outgoing_count=("transaction_id", "count"),
        )
        .rename(
            columns={
                "source_entity": "middle_entity",
                "destination_entity": "last_entity",
                "date": "date_out",
            }
        )
    )

    circuits = []

    for middle_entity in incoming["middle_entity"].unique():

        incoming_group = incoming[
            incoming["middle_entity"] == middle_entity
        ].copy()

        outgoing_group = outgoing[
            outgoing["middle_entity"] == middle_entity
        ].copy()

        if incoming_group.empty or outgoing_group.empty:
            continue

        incoming_group = incoming_group.sort_values("date_in")
        outgoing_group = outgoing_group.sort_values("date_out")

        # Le middle_entity est déjà connu par la boucle.
        # On le retire pour éviter les conflits de colonnes
        # lors du merge_asof.
        outgoing_group = outgoing_group.drop(
            columns=["middle_entity"]
        )

        matches = pd.merge_asof(
            incoming_group,
            outgoing_group,
            left_on="date_in",
            right_on="date_out",
            direction="forward",
            tolerance=pd.Timedelta(days=14),
        )

        matches = matches.dropna(subset=["last_entity"])

        if matches.empty:
            continue

        # Évite les faux circuits du type A -> B -> A
        # ainsi que les boucles B -> B.
        matches = matches[
            (matches["first_entity"] != matches["last_entity"])
            & (matches["first_entity"] != middle_entity)
            & (matches["last_entity"] != middle_entity)
        ]

        if matches.empty:
            continue

        matches["amount_difference"] = (
            (
                matches["outgoing_amount"]
                - matches["incoming_amount"]
            ).abs()
            / matches["incoming_amount"]
        )

        # On recherche des flux significatifs
        # avec des montants relativement proches.
        matches = matches[
            (matches["incoming_amount"] >= 250_000)
            & (matches["outgoing_amount"] >= 250_000)
            & (matches["amount_difference"] <= 0.20)
        ]

        if matches.empty:
            continue

        for _, row in matches.iterrows():

            if row["amount_difference"] <= 0.05:
                suspicion = "HIGH"
            elif row["amount_difference"] <= 0.10:
                suspicion = "MEDIUM"
            else:
                suspicion = "LOW"

            circuits.append(
                {
                    "first_entity": row["first_entity"],
                    "middle_entity": middle_entity,
                    "last_entity": row["last_entity"],
                    "date_in": row["date_in"],
                    "date_out": row["date_out"],
                    "incoming_amount": row["incoming_amount"],
                    "outgoing_amount": row["outgoing_amount"],
                    "amount_difference": row["amount_difference"],
                    "incoming_count": row["incoming_count"],
                    "outgoing_count": row["outgoing_count"],
                    "suspicion": suspicion,
                }
            )

    if not circuits:
        return pd.DataFrame()

    result = pd.DataFrame(circuits)

    return result.sort_values(
        ["suspicion", "incoming_amount"],
        ascending=[True, False],
    )
    
def print_circuits(circuits):
    print()
    print("=" * 80)
    print("SUSPICIOUS FINANCIAL CIRCUITS")
    print("=" * 80)

    if circuits.empty:
        print("No suspicious financial circuit detected.")
        return

    display = circuits.copy()

    display["date_in"] = display["date_in"].dt.strftime("%Y-%m-%d")
    display["date_out"] = display["date_out"].dt.strftime("%Y-%m-%d")

    display["incoming_amount"] = display["incoming_amount"].map(
        lambda x: f"{x:,.2f}"
    )

    display["outgoing_amount"] = display["outgoing_amount"].map(
        lambda x: f"{x:,.2f}"
    )

    display["amount_difference"] = (
        display["amount_difference"] * 100
    ).map(
        lambda x: f"{x:.2f}%"
    )

    print()

    for index, row in display.reset_index(drop=True).iterrows():
        print(f"CIRCUIT #{index + 1}")
        print("-" * 80)
        print(
            f"{row['first_entity']}"
            f" -> {row['middle_entity']}"
            f" -> {row['last_entity']}"
        )
        print(
            f"Incoming : {row['incoming_amount']}"
            f" | {row['date_in']}"
        )
        print(
            f"Outgoing : {row['outgoing_amount']}"
            f" | {row['date_out']}"
        )
        print(
            f"Difference : {row['amount_difference']}"
            f" | Suspicion : {row['suspicion']}"
        )
        print(
            f"Transactions : "
            f"{row['incoming_count']} incoming / "
            f"{row['outgoing_count']} outgoing"
        )
        print()

def main():
    transactions, accounts, entities = load_data()

    data = build_transaction_view(
        transactions,
        accounts,
        entities,
    )

    scores = generate_investigation_report(
        data
    )

    print_report(scores)

    circuits = detect_circuits(data)

    circuits = enrich_circuits(
        circuits,
        entities,
    )

    print_circuits(circuits)


if __name__ == "__main__":
    main()