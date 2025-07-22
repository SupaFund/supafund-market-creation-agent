import subprocess
import logging
import shlex
from typing import Tuple
from .config import Config

logger = logging.getLogger(__name__)


def place_bet(
    market_id: str,
    amount_usd: float,
    outcome: str,
    from_private_key: str,
    safe_address: str = None,
    auto_deposit: bool = True
) -> Tuple[bool, str]:
    """
    Place a bet on an Omen market by executing an external script.
    
    Args:
        market_id: The market ID to bet on
        amount_usd: The amount to bet in USD
        outcome: The outcome to bet on (e.g., 'Yes' or 'No')
        from_private_key: The private key to use for the bet
        safe_address: Optional safe address to use for the bet
        auto_deposit: Whether to automatically deposit collateral token
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        logger.info(f"Placing bet on market {market_id} for {amount_usd} USD on outcome {outcome}")
        
        poetry_executable_path = Config.POETRY_PATH
        project_path = Config.OMEN_SCRIPT_PROJECT_PATH
        
        # Build the command to execute the bet script
        command = [
            "/bin/sh",
            poetry_executable_path,
            "run",
            "python",
            "scripts/bet_omen.py",
            "buy",
            "--amount-usd", str(amount_usd),
            "--from-private-key", from_private_key,
            "--market-id", market_id,
            "--outcome", outcome,
        ]
        
        # Add auto-deposit flag if enabled (typer boolean options are flags)
        if auto_deposit:
            command.append("--auto-deposit")
        else:
            command.append("--no-auto-deposit")
        
        # Add safe address if provided
        if safe_address:
            command.extend(["--safe-address", safe_address])
        
        logger.info(f"Executing command: {' '.join(shlex.quote(c) for c in command)}")
        
        # Set up environment variables for the subprocess
        import os
        env = os.environ.copy()
        
        # Make sure all necessary environment variables are available in the subprocess
        if hasattr(Config, 'GRAPH_API_KEY') and Config.GRAPH_API_KEY:
            env['GRAPH_API_KEY'] = Config.GRAPH_API_KEY
        
        # Also pass the private key environment variable
        if hasattr(Config, 'OMEN_PRIVATE_KEY') and Config.OMEN_PRIVATE_KEY:
            env['BET_FROM_PRIVATE_KEY'] = Config.OMEN_PRIVATE_KEY
        
        # Execute the command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            cwd=project_path,
            env=env
        )
        
        logger.info(f"Bet placed successfully. Output:\n{result.stdout}")
        return True, f"Bet placed successfully. Output: {result.stdout}"
        
    except subprocess.CalledProcessError as e:
        error_message = (
            f"Bet placement failed with exit code {e.returncode}.\n"
            f"Stderr: {e.stderr}\n"
            f"Stdout: {e.stdout}"
        )
        logger.error(error_message)
        return False, error_message
        
    except FileNotFoundError as e:
        error_message = f"Subprocess error: File not found. The system failed to execute '{e.filename}'. Full error: {e}"
        logger.error(error_message)
        return False, error_message
        
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        return False, str(e)