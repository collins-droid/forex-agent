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
    
    def analyze_market(self, screenshot_base64: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Analyze the market using OmniParser.
        
        Args:
            screenshot_base64: Base64-encoded screenshot of the chart
            
        Returns:
            Tuple containing the parsed market data and the raw parsed_content_list
        """
        try:
            # Send the screenshot to OmniParser
            logger.info("Sending screenshot to OmniParser for analysis")
            
            response = self._call_omniparser(screenshot_base64)
            parsed_content_list = response.get('parsed_content_list', [])
            market_data = self._extract_forex_data(parsed_content_list)
            
            logger.info("Market analysis completed successfully")
            return market_data, parsed_content_list
            
        except Exception as e:
            logger.error(f"Error analyzing market: {str(e)}")
            raise
    
    def _call_omniparser(self, screenshot_base64: str) -> Dict[str, Any]:
        """
        Call the OmniParser service with a screenshot.
        
        Args:
            screenshot_base64: Base64-encoded screenshot of the chart
            
        Returns:
            Dict containing the OmniParser response
        """
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
        return response.json()
    
    def _extract_forex_data(self, parsed_content_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract relevant forex data from the OmniParser parsed_content_list.
        
        Args:
            parsed_content_list: List of parsed content items from OmniParser
            
        Returns:
            Dict containing structured forex data
        """
        forex_data = {
            "currency_pair": self.currency_pair,
            "timestamp": datetime.now().isoformat(),
            "candlestick_patterns": [],
            "indicators": {},
            "price_levels": {},
            "parsed_elements_count": len(parsed_content_list)
        }
        
        for item in parsed_content_list:
            content = item.get('content', '').lower()
            if not content: 
                continue
            
            # Extract candlestick patterns
            if "bullish engulfing" in content:
                forex_data["candlestick_patterns"].append("bullish_engulfing")
            elif "bearish engulfing" in content:
                forex_data["candlestick_patterns"].append("bearish_engulfing")
            elif "doji" in content:
                forex_data["candlestick_patterns"].append("doji")
            elif "hammer" in content:
                forex_data["candlestick_patterns"].append("hammer")
            elif "shooting star" in content:
                forex_data["candlestick_patterns"].append("shooting_star")
            
            # Extract RSI values
            elif "rsi" in content:
                try:
                    # Try multiple formats: "RSI: 25.5%", "RSI: 25.5", "RSI 25.5"
                    if ":" in content:
                        rsi_str = content.split("rsi:")[1].strip().split()[0].replace('%', '')
                    else:
                        rsi_str = content.split("rsi")[1].strip().split()[0].replace('%', '')
                    forex_data["indicators"]["RSI"] = float(rsi_str)
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse RSI: {content}")
                
            # Extract price levels
            elif "bid" in content:
                try:
                    bid_parts = content.split("bid:")
                    if len(bid_parts) > 1:
                        bid = float(bid_parts[1].strip().split()[0])
                        forex_data["price_levels"]["bid"] = bid
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse bid: {content}")
            elif "ask" in content:
                try:
                    ask_parts = content.split("ask:")
                    if len(ask_parts) > 1:
                        ask = float(ask_parts[1].strip().split()[0])
                        forex_data["price_levels"]["ask"] = ask
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse ask: {content}")
            elif "support" in content:
                try:
                    support_parts = content.split("support:")
                    if len(support_parts) > 1:
                        support = float(support_parts[1].strip().split()[0])
                        forex_data["price_levels"]["support"] = support
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse support: {content}")
            elif "resistance" in content:
                try:
                    resistance_parts = content.split("resistance:")
                    if len(resistance_parts) > 1:
                        resistance = float(resistance_parts[1].strip().split()[0])
                        forex_data["price_levels"]["resistance"] = resistance
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse resistance: {content}")
            
            # Extract MACD values
            elif "macd" in content:
                try:
                    if ":" in content:
                        macd_str = content.split("macd:")[1].strip().split()[0]
                    else:
                        macd_str = content.split("macd")[1].strip().split()[0]
                    forex_data["indicators"]["MACD"] = float(macd_str)
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse MACD: {content}")
        
        logger.info(f"Extracted Forex Data: {forex_data}")
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
        # Get recent trade history (up to 3 most recent trades)
        history = self.trade_history[-3:] if self.trade_history else []
        history_str = json.dumps(history, indent=2) if history else "None"
        
        prompt = f"""
        You are a Forex trading AI for Exness on {self.currency_pair}.
        OmniParser data:
        ```json
        {json.dumps(market_data, indent=2)}
        ```
        Recent trades:
        ```json
        {history_str}
        ```
        Strategy: Buy if bullish engulfing and RSI < 30; Sell if bearish engulfing and RSI > 70; else Hold.
        Instructions:
        1. Analyze OmniParser data step-by-step.
        2. Use history to avoid repeated errors.
        3. Output: {{"action": "buy/sell/hold", "reasoning": "your logic"}}
        """
        
        return prompt
    
    def make_trade_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a trade decision based on market data using an LLM.
        
        Args:
            market_data: Structured forex market data
            
        Returns:
            Dict containing the trading decision
        """
        prompt = self._construct_prompt(market_data)
        
        try:
            # Call OpenAI API
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}"
                },
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 200,
                    "response_format": {"type": "json_object"}
                },
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"LLM error: {response.status_code}, {response.text}")
                return {"action": "hold", "reasoning": f"Error: LLM returned {response.status_code}", "reward": 0}
            
            # Parse the response and ensure it's valid JSON
            try:
                decision = json.loads(response.choices[0].message.content)
                # Validate the decision contains the expected fields
                if "action" not in decision or "reasoning" not in decision:
                    raise ValueError("Decision missing required fields")
                
                # Assign reward based on action (simple example)
                decision["reward"] = 1 if decision["action"] in ["buy", "sell"] else 0
                
                return decision
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                return {"action": "hold", "reasoning": f"Error: Invalid JSON: {str(e)}", "reward": 0}
            except ValueError as e:
                logger.error(f"Invalid decision format: {e}")
                return {"action": "hold", "reasoning": f"Error: {str(e)}", "reward": 0}
            
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {"action": "hold", "reasoning": f"Error: {str(e)}", "reward": 0}
    
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

    def log_trade(self, trade: Dict[str, Any], market_data: Dict[str, Any], parsed_content_list: List[Dict[str, Any]]) -> None:
        """
        Log a trade to the trade history.
        
        Args:
            trade: The trade decision
            market_data: The market data that led to the decision
            parsed_content_list: The raw OmniParser output
        """
        trade_log = {
            "timestamp": trade.get("timestamp", datetime.now().isoformat()),
            "currency_pair": self.currency_pair,
            "action": trade["action"],
            "reasoning": trade["reasoning"],
            "reward": trade["reward"],
            "market_data": market_data,
            "parsed_content_list": parsed_content_list
        }
        
        self.trade_history.append(trade_log)
        logger.info(f"Trade logged: {trade_log}")
        
        # Optionally, you could save to a database or file here
        try:
            with open(f"{self.currency_pair}_trade_history.json", 'w') as f:
                json.dump(self.trade_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")

    def evaluate_performance(self) -> Dict[str, Any]:
        """
        Evaluate the trading performance based on trade history.
        
        Returns:
            Dict containing performance metrics
        """
        if not self.trade_history:
            return {"win_rate": 0.0, "total_trades": 0, "active_trades": 0}
        
        # Count trades that are not "hold"
        trades = [t for t in self.trade_history if t["action"] != "hold"]
        total_trades = len(trades)
        
        if total_trades == 0:
            return {"win_rate": 0.0, "total_trades": 0, "active_trades": 0}
        
        # Count wins (simple example - in a real scenario, this would be based on actual PnL)
        wins = sum(1 for t in trades if t.get("reward", 0) > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        
        # Calculate position duration - just an example
        trades_with_timestamps = [(t, datetime.fromisoformat(t["timestamp"])) for t in trades]
        trades_with_timestamps.sort(key=lambda x: x[1])  # Sort by timestamp
        
        # Count currently active trades (could be modified to track actual open positions)
        active_trades = sum(1 for t in trades if t.get("status") == "open")
        
        metrics = {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "active_trades": active_trades,
            "last_trade_time": trades_with_timestamps[-1][1].isoformat() if trades_with_timestamps else None
        }
        
        logger.info(f"Performance metrics: {metrics}")
        return metrics

# Example usage:
# agent = TradingAgent(openai_api_key="your_key", omniparser_url="http://localhost:8000")
# market_data, parsed_content_list = agent.analyze_market(screenshot_base64)
# decision = agent.decide_trade(market_data)
# if decision["action"] != "hold":
#     # Execute trade
#     # ...
#     # Log trade
#     agent.log_performance(decision, profit=0.5)  # Profit in units of base currency 