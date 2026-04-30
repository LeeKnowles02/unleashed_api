from __future__ import annotations

from db import get_conn
from exchange_rates_service import load_latest_exchange_rates


def test_db_connection() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        row = cur.fetchone()
        print(f"DB connection test result: {row[0]}")


def print_latest_rates(limit: int = 10) -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP (?)
                RateDate,
                BaseCurrency,
                QuoteCurrency,
                Rate,
                Provider,
                LoadedAtUTC
            FROM unleashed.ExchangeRates
            ORDER BY RateDate DESC, QuoteCurrency ASC
            """,
            limit,
        )
        rows = cur.fetchall()

    print(f"\nLatest {len(rows)} row(s) from unleashed.ExchangeRates:")
    for row in rows:
        print(
            f"- RateDate={row[0]}, Base={row[1]}, Quote={row[2]}, "
            f"Rate={row[3]}, Provider={row[4]}, LoadedAtUTC={row[5]}"
        )


def main() -> None:
    print("=== Exchange Rates Loader Test ===")
    test_db_connection()
    result = load_latest_exchange_rates()
    print(
        "Load completed: "
        f"rows_loaded={result['rows_loaded']}, "
        f"rate_date={result['rate_date']}, "
        f"base_currency={result['base_currency']}, "
        f"quotes={','.join(result['quote_currencies'])}, "
        f"provider={result['provider']}"
    )
    print_latest_rates(limit=12)


if __name__ == "__main__":
    main()
