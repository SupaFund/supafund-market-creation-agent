import csv
import typer
from web3 import Web3

from prediction_market_agent_tooling.config import APIKeys
from prediction_market_agent_tooling.gtypes import USD, OutcomeStr, private_key_type
from prediction_market_agent_tooling.loggers import logger
from prediction_market_agent_tooling.markets.omen.data_models import (
    OMEN_BINARY_MARKET_OUTCOMES,
    OmenMarket,
)
from prediction_market_agent_tooling.markets.omen.omen import omen_create_market_tx
from prediction_market_agent_tooling.markets.omen.omen_contracts import (
    COLLATERAL_TOKEN_CHOICE_TO_ADDRESS,
    OMEN_DEFAULT_MARKET_FEE_PERC,
    CollateralTokenChoice,
)
from prediction_market_agent_tooling.tools.utils import DatetimeUTC

QUESTION_COLUMN = "Question"
CLOSING_DATE_COLUMN = "Closing date"


def main(
    path: str,
    category: str = typer.Option(),
    initial_funds_usd: str = typer.Option(),
    from_private_key: str = typer.Option(),
    safe_address: str = typer.Option(None),
    cl_token: CollateralTokenChoice = CollateralTokenChoice.sdai,
    fee_perc: float = typer.Option(OMEN_DEFAULT_MARKET_FEE_PERC),
    language: str = typer.Option("en"),
    outcomes: list[str] = typer.Option(OMEN_BINARY_MARKET_OUTCOMES),
    auto_deposit: bool = typer.Option(True),
) -> None:
    """
    Helper script to create markets on Omen, usage:

    ```bash
    python scripts/create_markets_from_sheet_omen.py \
        devconflict.csv \
        --category devconflict \
        --initial-funds 10 \
        --auto-deposit \
        --from-private-key your-private-key
    ```
    """
    # Read CSV data using built-in csv module
    data_rows = []
    with open(path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        columns = reader.fieldnames or []
        
        # Check required columns
        required_columns = [QUESTION_COLUMN, CLOSING_DATE_COLUMN]
        if not all(column in columns for column in required_columns):
            missing_cols = [col for col in required_columns if col not in columns]
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Process rows
        for row in reader:
            # Skip rows with missing questions
            question = row.get(QUESTION_COLUMN, '').strip()
            if not question:
                continue
                
            # Parse closing date
            try:
                closing_date = DatetimeUTC.to_datetime_utc(row[CLOSING_DATE_COLUMN])
                data_rows.append({
                    QUESTION_COLUMN: question,
                    CLOSING_DATE_COLUMN: closing_date
                })
            except Exception as e:
                logger.warning(f"Failed to parse date for question '{question}': {e}")
                continue

    logger.info(f"Will create {len(data_rows)} markets:")
    for row in data_rows:
        logger.info(f"Question: {row[QUESTION_COLUMN]}, Closing: {row[CLOSING_DATE_COLUMN]}")

    safe_address_checksum = (
        Web3.to_checksum_address(safe_address) if safe_address else None
    )
    api_keys = APIKeys(
        BET_FROM_PRIVATE_KEY=private_key_type(from_private_key),
        SAFE_ADDRESS=safe_address_checksum,
    )

    for row in data_rows:
        logger.info(
            f"Going to create `{row[QUESTION_COLUMN]}` with closing time `{row[CLOSING_DATE_COLUMN]}`."
        )
        market = OmenMarket.from_created_market(
            omen_create_market_tx(
                api_keys=api_keys,
                collateral_token_address=COLLATERAL_TOKEN_CHOICE_TO_ADDRESS[cl_token],
                initial_funds=USD(initial_funds_usd),
                fee_perc=fee_perc,
                question=row[QUESTION_COLUMN],
                closing_time=row[CLOSING_DATE_COLUMN],
                category=category,
                language=language,
                outcomes=[OutcomeStr(x) for x in outcomes],
                auto_deposit=auto_deposit,
            )
        )
        logger.info(f"Market '{row[QUESTION_COLUMN]}' created at url: {market.url}.")


if __name__ == "__main__":
    typer.run(main)
