"""
Utility functions for the Forex Trading Agent
"""

import base64
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64-encoded string
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def decode_base64_to_image(base64_string: str, output_path: str) -> None:
    """
    Decode a base64 string to an image file.
    
    Args:
        base64_string: Base64-encoded string
        output_path: Path to save the image
    """
    with open(output_path, "wb") as image_file:
        image_file.write(base64.b64decode(base64_string))


def save_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        output_path: Path to save the JSON file
    """
    with open(output_path, "w") as json_file:
        json.dump(data, json_file, indent=2)


def load_json(input_path: str) -> Dict[str, Any]:
    """
    Load data from a JSON file.
    
    Args:
        input_path: Path to the JSON file
        
    Returns:
        Loaded data
    """
    with open(input_path, "r") as json_file:
        return json.load(json_file)


def generate_timestamp() -> str:
    """
    Generate a formatted timestamp.
    
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_trade_history(trade_history: List[Dict[str, Any]], output_dir: str) -> str:
    """
    Save trade history to a JSON file with timestamp.
    
    Args:
        trade_history: List of trade dictionaries
        output_dir: Directory to save the file
        
    Returns:
        Path to the saved file
    """
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    filename = f"trade_history_{generate_timestamp()}.json"
    output_path = os.path.join(output_dir, filename)
    
    # Save data
    save_json(trade_history, output_path)
    
    return output_path


def calculate_pip_value(currency_pair: str, lot_size: float) -> float:
    """
    Calculate the pip value for a given currency pair and lot size.
    
    Args:
        currency_pair: Currency pair (e.g., "EURUSD")
        lot_size: Size of the lot
        
    Returns:
        Pip value in the account currency
    """
    # A simplified implementation
    # In a real scenario, this would consider:
    # - The specific currency pair
    # - The account currency
    # - Current exchange rates
    # - Standard lot size (100,000 units)
    
    # Standard pip values for common pairs with USD as account currency
    pip_values = {
        "EURUSD": 10,
        "GBPUSD": 10,
        "USDJPY": 9.40,
        "AUDUSD": 10,
        "USDCHF": 10.60,
        "USDCAD": 7.60,
        "NZDUSD": 10
    }
    
    # Default to EURUSD if not found
    standard_pip_value = pip_values.get(currency_pair.upper(), 10)
    
    # Adjust for lot size (standard lot is 1.0)
    return standard_pip_value * (lot_size / 1.0)


def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    stop_loss_pips: int,
    currency_pair: str
) -> float:
    """
    Calculate the appropriate position size based on risk management.
    
    Args:
        account_balance: Current account balance
        risk_percentage: Percentage of account to risk (e.g., 2.0 for 2%)
        stop_loss_pips: Size of stop loss in pips
        currency_pair: Currency pair to trade
        
    Returns:
        Recommended lot size
    """
    # Calculate amount to risk
    risk_amount = account_balance * (risk_percentage / 100)
    
    # Calculate pip value for a standard lot
    standard_pip_value = calculate_pip_value(currency_pair, 1.0)
    
    # Calculate potential loss for the stop loss
    potential_loss_per_lot = stop_loss_pips * standard_pip_value
    
    # Calculate lot size
    if potential_loss_per_lot == 0:
        return 0
    
    lot_size = risk_amount / potential_loss_per_lot
    
    # Round to 2 decimal places (standard for most brokers)
    return round(lot_size, 2) 