"""
Forex Trading Agent
------------------
This module provides the TradingAgent class for analyzing Forex market screenshots,
making trading decisions, and logging performance.
"""

import json
import logging
import requests
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TradingAgent")

class TradingAgent:
    """
    A trading agent that analyzes market data from screenshots, 
    makes trading decisions, and logs performance.
    """
    
    def __init__(
        self, 
        openai_api_key: str,
        omniparser_url: str,
        currency_pair: str = "EURUSD",
        lot_size: float = 0.01
    ):
        """
        Initialize the trading agent.
        
        Args:
            openai_api_key: API key for OpenAI
            omniparser_url: URL of the OmniParser service
            currency_pair: The currency pair to trade
            lot_size: Size of trades to execute
        """
        self.openai_api_key = openai_api_key
        self.omniparser_url = omniparser_url
        self.currency_pair = currency_pair
        self.lot_size = lot_size
        self.trade_history = []
        
        logger.info(f"Trading agent initialized for {currency_pair} with lot size {lot_size}")
    
    def analyze_market(self, screenshot_base64: str) -> Dict[str, Any]:
        """
        Analyze the market using OmniParser.
        
        Args:
            screenshot_base64: Base64-encoded screenshot of the chart
            
        Returns:
            Dict containing the parsed market data
        """
        try:
            # Send the screenshot to OmniParser
            logger.info("Sending screenshot to OmniParser for analysis")
            
            response = requests.post(
                f"{self.omniparser_url}/parse/",
                json={"image": screenshot_base64},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"OmniParser returned error: {response.status_code}, {response.text}")
                raise Exception(f"OmniParser error: {response.status_code}")
            
            # Parse the response
            parsed_data = response.json()
            
            # Extract relevant forex data
            forex_data = self._extract_forex_data(parsed_data)
            
            logger.info("Market analysis completed successfully")
            return forex_data
            
        except Exception as e:
            logger.error(f"Error analyzing market: {str(e)}")
            raise
    
    def _extract_forex_data(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant forex data from the OmniParser response.
        
        Args:
            parsed_data: Raw data from OmniParser
            
        Returns:
            Dict containing structured forex data
        """
        # This is a simplified implementation
        # A real implementation would have more sophisticated logic to extract
        # candlesticks, indicators, support/resistance levels, etc.
        
        forex_data = {
            "currency_pair": self.currency_pair,
            "timestamp": datetime.now().isoformat(),
            "candlesticks": [],
            "indicators": {},
            "price": {
                "current": None,
                "high": None,
                "low": None
            },
            "support_resistance": [],
            "trend": None
        }
        
        # Extract candlesticks if available
        if "candlesticks" in parsed_data:
            forex_data["candlesticks"] = parsed_data["candlesticks"]
        
        # Extract current price if available
        if "price" in parsed_data:
            forex_data["price"]["current"] = parsed_data["price"].get("current")
            forex_data["price"]["high"] = parsed_data["price"].get("high")
            forex_data["price"]["low"] = parsed_data["price"].get("low")
        
        # Extract indicators if available
        indicators_to_extract = ["rsi", "macd", "bollinger_bands", "moving_averages"]
        for indicator in indicators_to_extract:
            if indicator in parsed_data:
                forex_data["indicators"][indicator] = parsed_data[indicator]
        
        # Extract support/resistance levels if available
        if "support_resistance" in parsed_data:
            forex_data["support_resistance"] = parsed_data["support_resistance"]
        
        # Extract trend if available
        if "trend" in parsed_data:
            forex_data["trend"] = parsed_data["trend"]
        
        return forex_data
    
    def decide_trade(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide whether to make a trade based on market data.
        
        Args:
            market_data: Structured forex market data
            
        Returns:
            Dict containing the trading decision
        """
        try:
            # Construct prompt for LLM
            prompt = self._construct_prompt(market_data)
            
            # Call OpenAI API
            logger.info("Requesting trading decision from LLM")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}"
                },
                json={
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert forex trading assistant. Analyze the market data and provide trading advice in JSON format with action and reasoning fields."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI API returned error: {response.status_code}, {response.text}")
                raise Exception(f"OpenAI API error: {response.status_code}")
            
            # Parse the response
            result = response.json()
            decision_text = result["choices"][0]["message"]["content"]
            decision = json.loads(decision_text)
            
            # Validate decision format
            if not decision.get("action") or not decision.get("reasoning"):
                logger.error(f"Invalid decision format: {decision}")
                raise Exception("Invalid decision format from LLM")
            
            # Ensure action is one of: buy, sell, hold
            if decision["action"] not in ["buy", "sell", "hold"]:
                logger.warning(f"Invalid action '{decision['action']}' from LLM, defaulting to 'hold'")
                decision["action"] = "hold"
            
            logger.info(f"Trading decision: {decision['action']} - {decision['reasoning']}")
            
            # Add timestamp to decision
            decision["timestamp"] = datetime.now().isoformat()
            decision["currency_pair"] = self.currency_pair
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making trading decision: {str(e)}")
            # Default to "hold" when there's an error
            return {
                "action": "hold",
                "reasoning": f"Error getting trading decision: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "currency_pair": self.currency_pair
            }
    
    def _construct_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Construct a prompt for the LLM based on market data and trade history.
        
        Args:
            market_data: Structured forex market data
            
        Returns:
            Formatted prompt string
        """
        # Recent trade history (up to 5 most recent trades)
        recent_trades = ""
        for i, trade in enumerate(self.trade_history[-5:]):
            trade_time = datetime.fromisoformat(trade["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            recent_trades += f"Trade {i+1}: {trade['action'].upper()} at {trade_time} - Reasoning: {trade['reasoning']}\n"
        
        if not recent_trades:
            recent_trades = "No previous trades"
        
        return f"""
Please analyze this forex market data and make a trading decision.

MARKET DATA:
{json.dumps(market_data, indent=2)}

RECENT TRADE HISTORY:
{recent_trades}

Based on the market data from OmniParser, decide whether to:
1. BUY (if you see a strong upward trend or oversold condition)
2. SELL (if you see a strong downward trend or overbought condition)
3. HOLD (if the market direction is unclear or risk is too high)

Consider:
- Candlestick patterns
- Trend direction and strength
- Support and resistance levels
- Technical indicators visible in the chart
- Recent price action

IMPORTANT:
- Focus on risk management
- Only trade with clear signals
- Default to HOLD if uncertain

Respond with a JSON object containing:
{
  "action": "buy|sell|hold",
  "reasoning": "brief explanation of your decision"
}
"""
    
    def log_performance(self, trade: Dict[str, Any], profit: Optional[float] = None) -> None:
        """
        Log the performance of a completed trade.
        
        Args:
            trade: The trade information
            profit: The profit/loss of the trade (positive for profit, negative for loss)
        """
        # Add profit information if provided
        if profit is not None:
            trade["profit"] = profit
        
        # Add to trade history
        self.trade_history.append(trade)
        
        # Keep only the last n trades to avoid excessive memory usage
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        # Log the trade
        action = trade["action"].upper()
        reasoning = trade["reasoning"]
        profit_str = f" with profit {profit}" if profit is not None else ""
        logger.info(f"Logged trade: {action}{profit_str} - {reasoning}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate and return performance metrics.
        
        Returns:
            Dict containing performance metrics
        """
        # Only consider trades with profit information
        trades_with_profit = [t for t in self.trade_history if "profit" in t and t["profit"] is not None]
        
        total_trades = len(trades_with_profit)
        if total_trades == 0:
            return {
                "win_rate": 0,
                "profit_loss": 0,
                "total_trades": 0,
                "average_profit": 0,
                "average_loss": 0
            }
        
        # Calculate metrics
        winning_trades = [t for t in trades_with_profit if t["profit"] > 0]
        losing_trades = [t for t in trades_with_profit if t["profit"] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        profit_loss = sum(t["profit"] for t in trades_with_profit)
        
        avg_profit = sum(t["profit"] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t["profit"] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            "win_rate": win_rate,
            "profit_loss": profit_loss,
            "total_trades": total_trades,
            "average_profit": avg_profit,
            "average_loss": avg_loss
        }

# Example usage:
# agent = TradingAgent(openai_api_key="your_key", omniparser_url="http://localhost:8000")
# market_data = agent.analyze_market(screenshot_base64)
# decision = agent.decide_trade(market_data)
# if decision["action"] != "hold":
#     # Execute trade
#     # ...
#     # Log trade
#     agent.log_performance(decision, profit=0.5)  # Profit in units of base currency 