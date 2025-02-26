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
import re
import copy

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
    
    def analyze_market(self, screenshot_base64: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
        """
        Analyze the forex market using OmniParser and make trade decisions.
        
        Args:
            screenshot_base64: Base64-encoded screenshot of the chart
            
        Returns:
            Tuple containing:
            - Dict with market data
            - List of parsed content from OmniParser
            - String with base64-encoded labeled image
        """
        try:
            logger.info("Starting market analysis with OmniParser")
            
            # Call OmniParser to get parsed content and labeled image
            response = self._call_omniparser(screenshot_base64)
            parsed_content_list = response.get('parsed_content_list', [])
            dino_labeled_img = response.get('dino_labeled_img', '')
            
            # Extract relevant data from parsed content
            forex_data = self._extract_forex_data(parsed_content_list)
            
            logger.info(f"Market analysis complete: {len(parsed_content_list)} items parsed")
            return forex_data, parsed_content_list, dino_labeled_img
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            # Return empty data on error
            return {
                "currency_pair": self.currency_pair,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }, [], ""
    
    def _calculate_confidence_score(self, forex_data: Dict[str, Any]) -> float:
        """
        Calculate a confidence score based on the forex data patterns and indicators.
        
        Args:
            forex_data: Structured forex data from _extract_forex_data
            
        Returns:
            Float between 0.0 and 1.0 representing confidence level
        """
        score = 0.5  # Start with neutral score
        
        # Check for candlestick patterns
        bullish_patterns = ["bullish_engulfing", "hammer", "morning_star", "tweezer_bottom"]
        bearish_patterns = ["bearish_engulfing", "shooting_star", "evening_star", "tweezer_top"]
        
        # Adjust for candlestick patterns
        for pattern in forex_data.get("candlestick_patterns", []):
            if pattern in bullish_patterns:
                score += 0.1
            elif pattern in bearish_patterns:
                score -= 0.1
        
        # Adjust for trend
        if forex_data.get("trend") == "up":
            score += 0.15
        elif forex_data.get("trend") == "down":
            score -= 0.15
        
        # Adjust for RSI
        if "RSI" in forex_data.get("indicators", {}):
            rsi = forex_data["indicators"]["RSI"]
            if rsi < 30:  # Oversold
                score += 0.1
            elif rsi > 70:  # Overbought
                score -= 0.1
        
        # Adjust for MACD
        if "MACD" in forex_data.get("indicators", {}):
            macd = forex_data["indicators"]["MACD"]
            if macd > 0:
                score += 0.1
            elif macd < 0:
                score -= 0.1
        
        # Adjust for price levels
        if "bid" in forex_data.get("price_levels", {}) and "support" in forex_data.get("price_levels", {}):
            if forex_data["price_levels"]["bid"] <= forex_data["price_levels"]["support"] * 1.01:
                score += 0.1  # Price near support level, potential bounce
        
        if "ask" in forex_data.get("price_levels", {}) and "resistance" in forex_data.get("price_levels", {}):
            if forex_data["price_levels"]["ask"] >= forex_data["price_levels"]["resistance"] * 0.99:
                score -= 0.1  # Price near resistance level, potential reversal
        
        # Ensure score is between 0 and 1
        score = max(0, min(1, score))
        
        logger.info(f"Calculated confidence score: {score}")
        return score
    
    def _assess_risk(self, forex_data: Dict[str, Any], trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess risk based on market conditions and trading history.
        
        Args:
            forex_data: Structured forex data from _extract_forex_data
            trade_history: List of previous trades
            
        Returns:
            Dict containing risk assessment parameters
        """
        # Initialize risk assessment
        risk_assessment = {
            "level": "medium",
            "stop_loss_pips": 15,  # Default stop loss
            "take_profit_pips": 30,  # Default take profit
            "position_size": 1.0,  # Default position size
            "max_exposure": 3.0,    # Maximum total exposure
            "volatility_factor": 1.0,  # Volatility adjustment factor
            "confidence_threshold": 0.65  # Minimum confidence for trades
        }
        
        # Check recent trade history for losses
        consecutive_losses = 0
        recent_trades = trade_history[-10:] if len(trade_history) >= 10 else trade_history
        
        for trade in reversed(recent_trades):
            if trade.get("outcome") == "loss":
                consecutive_losses += 1
            else:
                break
        
        # Adjust risk based on consecutive losses (progressive risk reduction)
        if consecutive_losses >= 5:
            risk_assessment["level"] = "extreme"
            risk_assessment["position_size"] = 0.25  # Severely reduce position size
            risk_assessment["stop_loss_pips"] = 8    # Very tight stop loss
            risk_assessment["confidence_threshold"] = 0.85  # Require high confidence
            logger.warning(f"Extreme risk detected: {consecutive_losses} consecutive losses")
        elif consecutive_losses >= 3:
            risk_assessment["level"] = "high"
            risk_assessment["position_size"] = 0.5   # Reduce position size
            risk_assessment["stop_loss_pips"] = 10   # Tighter stop loss
            risk_assessment["confidence_threshold"] = 0.75  # Require higher confidence
            logger.info(f"High risk detected: {consecutive_losses} consecutive losses")
        elif consecutive_losses == 0 and len(recent_trades) >= 5:
            # Check win rate in recent trades
            wins = sum(1 for t in recent_trades if t.get("outcome") == "win")
            win_rate = wins / len(recent_trades)
            
            if win_rate > 0.7:  # Over 70% win rate
                risk_assessment["level"] = "low"
                risk_assessment["position_size"] = 1.5  # Increase position size
                logger.info(f"Low risk detected: Win rate {win_rate:.2f}")
        
        # Adjust for volatility indicators
        if "ATR" in forex_data.get("indicators", {}):
            atr = forex_data["indicators"]["ATR"]
            # Scale stop loss and take profit based on ATR
            if isinstance(atr, (int, float)):
                # Higher ATR means more volatility
                volatility_multiplier = min(3.0, max(0.5, atr / 10.0))  # Cap between 0.5 and 3.0
                risk_assessment["volatility_factor"] = volatility_multiplier
                
                # Adjust stop loss and take profit proportionally to volatility
                risk_assessment["stop_loss_pips"] = max(8, int(risk_assessment["stop_loss_pips"] * volatility_multiplier))
                risk_assessment["take_profit_pips"] = max(16, int(risk_assessment["take_profit_pips"] * volatility_multiplier))
                
                logger.info(f"Volatility adjustment: factor {volatility_multiplier:.2f}, " 
                          f"SL: {risk_assessment['stop_loss_pips']}, TP: {risk_assessment['take_profit_pips']}")
        
        # Check current market trend against position direction (for existing positions)
        open_positions = [t for t in recent_trades if t.get("status") == "open"]
        if open_positions and forex_data.get("trend") != "neutral":
            # Calculate exposure by direction
            buy_exposure = sum(t.get("position_size", 1.0) for t in open_positions if t.get("direction") == "buy")
            sell_exposure = sum(t.get("position_size", 1.0) for t in open_positions if t.get("direction") == "sell")
            
            # If we have exposure against trend, reduce new position sizes
            if (forex_data["trend"] == "up" and sell_exposure > buy_exposure) or \
               (forex_data["trend"] == "down" and buy_exposure > sell_exposure):
                risk_assessment["position_size"] *= 0.75
                logger.info("Reduced position size due to counter-trend exposure")
        
        # Check for overbought/oversold conditions
        if "RSI" in forex_data.get("indicators", {}):
            rsi = forex_data["indicators"]["RSI"]
            if rsi < 20 or rsi > 80:  # Extreme RSI values
                risk_assessment["position_size"] *= 0.8  # Reduce position size in extreme conditions
                logger.info(f"Reduced position size due to extreme RSI: {rsi}")
        
        # Adjust for time of day (example: avoid trading during volatile news times)
        hour = datetime.now().hour
        if 13 <= hour <= 15:  # Example: US market open/news times (adjust for your timezone)
            risk_assessment["position_size"] *= 0.8
            logger.info("Reduced position size due to potentially volatile market hours")
        
        # Ensure position size respects maximum exposure
        total_exposure = sum(t.get("position_size", 1.0) for t in open_positions)
        if total_exposure + risk_assessment["position_size"] > risk_assessment["max_exposure"]:
            risk_assessment["position_size"] = max(0.1, risk_assessment["max_exposure"] - total_exposure)
            logger.info(f"Limited position size to {risk_assessment['position_size']} due to exposure cap")
        
        logger.info(f"Risk assessment: {risk_assessment}")
        return risk_assessment
    
    def make_trade_decision(self, forex_data: Dict[str, Any], confidence_score: float, 
                            risk_assessment: Dict[str, Any], trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Make a trade decision based on forex data, confidence score and risk assessment.
        
        Args:
            forex_data: Structured forex data from _extract_forex_data
            confidence_score: Confidence score from _calculate_confidence_score
            risk_assessment: Risk assessment from _assess_risk
            trade_history: List of previous trades
            
        Returns:
            Dict containing trade decision details
        """
        # Default to no trade
        decision = {
            "action": "hold",
            "direction": None,
            "confidence": confidence_score,
            "stop_loss_pips": risk_assessment["stop_loss_pips"],
            "take_profit_pips": risk_assessment["take_profit_pips"],
            "position_size": risk_assessment["position_size"],
            "strategies_triggered": [],
            "reasoning": []
        }
        
        # Define available trading strategies
        strategies = {
            "trend_following": self._apply_trend_following_strategy,
            "breakout": self._apply_breakout_strategy,
            "mean_reversion": self._apply_mean_reversion_strategy,
            "pattern_recognition": self._apply_pattern_recognition_strategy,
            "multi_timeframe": self._apply_multi_timeframe_strategy
        }
        
        # Check if we're in a valid market condition with sufficient data
        if not self._validate_market_conditions(forex_data):
            decision["reasoning"].append("Insufficient or invalid market data for reliable decision")
            logger.warning("Trade rejected due to insufficient or invalid market data")
            return decision
        
        # Apply each strategy and collect the signals
        strategy_signals = {}
        for strategy_name, strategy_func in strategies.items():
            try:
                signal = strategy_func(forex_data, risk_assessment, trade_history)
                if signal and signal.get("action") != "hold":
                    strategy_signals[strategy_name] = signal
                    logger.info(f"Strategy {strategy_name} triggered: {signal['action']} {signal.get('direction')}")
            except Exception as e:
                logger.error(f"Error applying strategy {strategy_name}: {str(e)}")
        
        # If no strategies triggered, hold
        if not strategy_signals:
            decision["reasoning"].append("No trading strategies triggered")
            logger.info("No trading signals triggered, holding position")
            return decision
        
        # Count signals in each direction
        buy_signals = sum(1 for s in strategy_signals.values() if s.get("direction") == "buy")
        sell_signals = sum(1 for s in strategy_signals.values() if s.get("direction") == "sell")
        
        # Determine final decision based on signal strength and risk assessment
        confidence_threshold = risk_assessment.get("confidence_threshold", 0.65)
        
        # Strongly aligned signals (3+ in same direction) or very high confidence
        if buy_signals >= 3 and sell_signals == 0:
            decision["action"] = "open"
            decision["direction"] = "buy"
            decision["strategies_triggered"] = [k for k, v in strategy_signals.items() if v.get("direction") == "buy"]
            decision["reasoning"].append(f"Strong buy consensus ({buy_signals} strategies)")
        elif sell_signals >= 3 and buy_signals == 0:
            decision["action"] = "open"
            decision["direction"] = "sell"
            decision["strategies_triggered"] = [k for k, v in strategy_signals.items() if v.get("direction") == "sell"]
            decision["reasoning"].append(f"Strong sell consensus ({sell_signals} strategies)")
        # Moderately aligned signals (2+ in same direction) with sufficient confidence
        elif buy_signals >= 2 and sell_signals == 0 and confidence_score >= confidence_threshold:
            decision["action"] = "open"
            decision["direction"] = "buy"
            decision["strategies_triggered"] = [k for k, v in strategy_signals.items() if v.get("direction") == "buy"]
            decision["reasoning"].append(f"Buy signal with good confidence ({confidence_score:.2f})")
        elif sell_signals >= 2 and buy_signals == 0 and confidence_score >= confidence_threshold:
            decision["action"] = "open"
            decision["direction"] = "sell"
            decision["strategies_triggered"] = [k for k, v in strategy_signals.items() if v.get("direction") == "sell"]
            decision["reasoning"].append(f"Sell signal with good confidence ({confidence_score:.2f})")
        # Conflicting signals or insufficient confidence
        else:
            if buy_signals > 0 and sell_signals > 0:
                decision["reasoning"].append(f"Conflicting signals: {buy_signals} buy vs {sell_signals} sell")
            elif confidence_score < confidence_threshold:
                decision["reasoning"].append(f"Insufficient confidence ({confidence_score:.2f} < {confidence_threshold})")
        
        # Apply risk management overrides
        if risk_assessment["level"] == "extreme" and decision["action"] == "open":
            decision["action"] = "hold"
            decision["direction"] = None
            decision["reasoning"].append("Trade aborted due to extreme risk level")
            logger.warning("Trade aborted due to extreme risk level")
        
        # Add data-based reasoning
        self._add_data_based_reasoning(decision, forex_data)
        
        # Log the decision
        logger.info(f"Trade decision: {json.dumps(decision, default=str)}")
        return decision
    
    def _validate_market_conditions(self, forex_data: Dict[str, Any]) -> bool:
        """
        Validate if the current market conditions have sufficient data for decision-making.
        
        Args:
            forex_data: Structured forex data from _extract_forex_data
            
        Returns:
            Boolean indicating if market conditions are valid
        """
        # Check if we have the minimum required data
        required_keys = ["price_levels", "indicators"]
        if not all(key in forex_data for key in required_keys):
            logger.warning(f"Missing required data in forex_data: {required_keys}")
            return False
        
        # Check for price data (minimum bid/ask)
        if not any(key in forex_data["price_levels"] for key in ["bid", "ask"]):
            logger.warning("No price data (bid/ask) available in forex_data")
            return False
        
        # Check for at least one technical indicator
        if not forex_data["indicators"]:
            logger.warning("No technical indicators available in forex_data")
            return False
        
        # Check for minimum parsed content
        if forex_data.get("parsed_elements_count", 0) < 3:
            logger.warning(f"Insufficient parsed elements: {forex_data.get('parsed_elements_count', 0)}")
            return False
        
        return True
    
    def _add_data_based_reasoning(self, decision: Dict[str, Any], forex_data: Dict[str, Any]) -> None:
        """
        Add reasoning based on forex data to the decision.
        
        Args:
            decision: Trade decision dict to update with reasoning
            forex_data: Structured forex data from _extract_forex_data
        """
        # Add pattern-based reasoning
        if forex_data.get("candlestick_patterns"):
            decision["reasoning"].append(f"Patterns: {', '.join(forex_data['candlestick_patterns'])}")
        
        # Add trend-based reasoning
        if forex_data.get("trend") != "neutral":
            decision["reasoning"].append(f"Market trend: {forex_data['trend']}")
        
        # Add indicator-based reasoning
        for indicator, value in forex_data.get("indicators", {}).items():
            if indicator in ["RSI", "MACD", "Stochastic"]:  # Key indicators
                decision["reasoning"].append(f"{indicator}: {value}")
    
    def _apply_trend_following_strategy(self, forex_data: Dict[str, Any], 
                                       risk_assessment: Dict[str, Any], 
                                       trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a trend following strategy to generate trading signals.
        
        Args:
            forex_data: Structured forex data
            risk_assessment: Risk assessment data
            trade_history: List of previous trades
            
        Returns:
            Dict containing the strategy signal
        """
        signal = {
            "action": "hold",
            "direction": None,
            "confidence": 0.0
        }
        
        # Trend following primarily uses the detected trend and supporting indicators
        trend = forex_data.get("trend", "neutral")
        
        # Check for strong trend with supporting indicators
        if trend == "up":
            # Confirm with MACD
            if forex_data.get("indicators", {}).get("MACD", 0) > 0:
                signal["action"] = "open"
                signal["direction"] = "buy"
                signal["confidence"] = 0.7
        elif trend == "down":
            # Confirm with MACD
            if forex_data.get("indicators", {}).get("MACD", 0) < 0:
                signal["action"] = "open"
                signal["direction"] = "sell"
                signal["confidence"] = 0.7
        
        return signal
    
    def _apply_breakout_strategy(self, forex_data: Dict[str, Any], 
                                 risk_assessment: Dict[str, Any], 
                                 trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a breakout strategy to generate trading signals.
        
        Args:
            forex_data: Structured forex data
            risk_assessment: Risk assessment data
            trade_history: List of previous trades
            
        Returns:
            Dict containing the strategy signal
        """
        signal = {
            "action": "hold",
            "direction": None,
            "confidence": 0.0
        }
        
        # Breakout strategy focuses on price levels
        price_levels = forex_data.get("price_levels", {})
        
        # Check for resistance breakout
        if "ask" in price_levels and "resistance" in price_levels:
            if price_levels["ask"] > price_levels["resistance"] * 1.002:  # 0.2% buffer for confirmation
                signal["action"] = "open"
                signal["direction"] = "buy"
                signal["confidence"] = 0.75
        
        # Check for support breakdown
        if "bid" in price_levels and "support" in price_levels:
            if price_levels["bid"] < price_levels["support"] * 0.998:  # 0.2% buffer for confirmation
                signal["action"] = "open"
                signal["direction"] = "sell"
                signal["confidence"] = 0.75
        
        return signal
    
    def _apply_mean_reversion_strategy(self, forex_data: Dict[str, Any], 
                                       risk_assessment: Dict[str, Any], 
                                       trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a mean reversion strategy to generate trading signals.
        
        Args:
            forex_data: Structured forex data
            risk_assessment: Risk assessment data
            trade_history: List of previous trades
            
        Returns:
            Dict containing the strategy signal
        """
        signal = {
            "action": "hold",
            "direction": None,
            "confidence": 0.0
        }
        
        indicators = forex_data.get("indicators", {})
        
        # Mean reversion uses overbought/oversold indicators
        if "RSI" in indicators:
            rsi = indicators["RSI"]
            
            # Oversold condition - potential buy signal
            if rsi < 30:
                signal["action"] = "open"
                signal["direction"] = "buy"
                signal["confidence"] = 0.6 + (30 - rsi) / 100  # Higher confidence for lower RSI
            
            # Overbought condition - potential sell signal
            elif rsi > 70:
                signal["action"] = "open"
                signal["direction"] = "sell"
                signal["confidence"] = 0.6 + (rsi - 70) / 100  # Higher confidence for higher RSI
        
        # Check Stochastic as well if available
        if "Stochastic" in indicators and isinstance(indicators["Stochastic"], str):
            stoch = indicators["Stochastic"].lower()
            
            if "oversold" in stoch and signal["direction"] == "buy":
                signal["confidence"] += 0.1  # Increase confidence if RSI and Stoch agree
            elif "overbought" in stoch and signal["direction"] == "sell":
                signal["confidence"] += 0.1  # Increase confidence if RSI and Stoch agree
        
        return signal
    
    def _apply_pattern_recognition_strategy(self, forex_data: Dict[str, Any], 
                                            risk_assessment: Dict[str, Any], 
                                            trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a pattern recognition strategy to generate trading signals.
        
        Args:
            forex_data: Structured forex data
            risk_assessment: Risk assessment data
            trade_history: List of previous trades
            
        Returns:
            Dict containing the strategy signal
        """
        signal = {
            "action": "hold",
            "direction": None,
            "confidence": 0.0
        }
        
        # Check for bullish patterns
        bullish_patterns = ["bullish_engulfing", "hammer", "morning_star", "tweezer_bottom"]
        bearish_patterns = ["bearish_engulfing", "shooting_star", "evening_star", "tweezer_top"]
        
        patterns = forex_data.get("candlestick_patterns", [])
        
        # Count bullish and bearish patterns
        bullish_count = sum(1 for p in patterns if p in bullish_patterns)
        bearish_count = sum(1 for p in patterns if p in bearish_patterns)
        
        # Generate signal based on pattern counts
        if bullish_count > 0 and bearish_count == 0:
            signal["action"] = "open"
            signal["direction"] = "buy"
            signal["confidence"] = 0.5 + (bullish_count * 0.1)  # More patterns, higher confidence
        elif bearish_count > 0 and bullish_count == 0:
            signal["action"] = "open"
            signal["direction"] = "sell"
            signal["confidence"] = 0.5 + (bearish_count * 0.1)  # More patterns, higher confidence
        
        return signal
    
    def _apply_multi_timeframe_strategy(self, forex_data: Dict[str, Any], 
                                       risk_assessment: Dict[str, Any], 
                                       trade_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply a multi-timeframe analysis strategy to generate trading signals.
        
        Args:
            forex_data: Structured forex data
            risk_assessment: Risk assessment data
            trade_history: List of previous trades
            
        Returns:
            Dict containing the strategy signal
        """
        # Note: In a real implementation, this would use data from multiple timeframes
        # For this prototype, we'll simulate it by using trend + indicators
        signal = {
            "action": "hold",
            "direction": None,
            "confidence": 0.0
        }
        
        # Extract trend and indicators
        trend = forex_data.get("trend", "neutral")
        indicators = forex_data.get("indicators", {})
        
        # Signal generation based on trend and multiple indicators
        if trend == "up" and indicators.get("RSI", 50) < 70:  # Not overbought
            # Check if MACD and other indicators confirm
            if indicators.get("MACD", 0) > 0:
                ema_rising = indicators.get("EMA", False)
                if ema_rising is True or (isinstance(ema_rising, (int, float)) and ema_rising > 0):
                    signal["action"] = "open"
                    signal["direction"] = "buy"
                    signal["confidence"] = 0.8
        
        elif trend == "down" and indicators.get("RSI", 50) > 30:  # Not oversold
            # Check if MACD and other indicators confirm
            if indicators.get("MACD", 0) < 0:
                ema_falling = indicators.get("EMA", False)
                if ema_falling is True or (isinstance(ema_falling, (int, float)) and ema_falling < 0):
                    signal["action"] = "open"
                    signal["direction"] = "sell"
                    signal["confidence"] = 0.8
        
        return signal
    
    def _call_omniparser(self, screenshot_base64: str) -> Dict[str, Any]:
        """
        Call the OmniParser service with a screenshot, with enhanced parameters for forex chart focus.
        
        Args:
            screenshot_base64: Base64-encoded screenshot of the chart
            
        Returns:
            Dict containing the OmniParser response with parsed content and labeled image
        """
        try:
            response = requests.post(
                f"{self.omniparser_url}/parse/",
                json={
                    "base64_image": screenshot_base64, 
                    "focus": "forex_chart", 
                    "box_threshold": 0.05, 
                    "iou_threshold": 0.1
                },
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"OmniParser returned error: {response.status_code}, {response.text}")
                raise Exception(f"OmniParser error: {response.status_code}")
            
            # Parse the response
            return response.json()
        except requests.RequestException as e:
            logger.error(f"OmniParser request failed: {e}")
            raise Exception(f"OmniParser error: {e}")
    
    def _extract_forex_data(self, parsed_content_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract forex trading data from OmniParser's parsed content list.
        Enhanced to handle icon detection and comprehensive text parsing.
        
        Args:
            parsed_content_list: List of parsed content from OmniParser
            
        Returns:
            Dict containing extracted forex data
        """
        forex_data = {
            "currency_pair": self.currency_pair,
            "timestamp": datetime.now().isoformat(),
            "candlestick_patterns": [],
            "indicators": {},
            "price_levels": {},
            "trend": "neutral",
            "icons_detected": [],
            "parsed_elements_count": len(parsed_content_list),
            "text_elements": []
        }
        
        # Log the number of elements detected
        logger.info(f"Processing {len(parsed_content_list)} elements from OmniParser")
        
        for item in parsed_content_list:
            content = item.get('content', '').lower()
            item_type = item.get('type', '')
            
            # Skip empty content
            if not content: 
                continue
                
            # Process different types of elements
            if item_type == 'icon':
                # Add to icons detected list
                forex_data["icons_detected"].append(content)
                
                # Check for candlestick patterns in icons
                if "candlestick" in content or "pattern" in content:
                    if "bullish" in content:
                        forex_data["candlestick_patterns"].append("bullish_pattern")
                    elif "bearish" in content:
                        forex_data["candlestick_patterns"].append("bearish_pattern")
                    elif "doji" in content:
                        forex_data["candlestick_patterns"].append("doji")
                
                # Check for trend indicators in icons
                if "trend" in content:
                    if "up" in content or "bullish" in content:
                        forex_data["trend"] = "up"
                    elif "down" in content or "bearish" in content:
                        forex_data["trend"] = "down"
            
            # Process text elements for more detailed information
            elif item_type == 'text':
                # Add to text elements for analysis
                forex_data["text_elements"].append(content)
                
                # Define patterns to look for in text
                patterns = {
                    "bullish engulfing": "bullish_engulfing",
                    "bearish engulfing": "bearish_engulfing",
                    "doji": "doji",
                    "hammer": "hammer",
                    "shooting star": "shooting_star",
                    "morning star": "morning_star",
                    "evening star": "evening_star",
                    "pinbar": "pinbar",
                    "tweezer top": "tweezer_top",
                    "tweezer bottom": "tweezer_bottom"
                }
                
                # Check for candlestick patterns in text
                for pattern, key in patterns.items():
                    if pattern in content:
                        forex_data["candlestick_patterns"].append(key)
                
                # Process trend information
                if "trend" in content:
                    if "uptrend" in content or "bullish trend" in content:
                        forex_data["trend"] = "up"
                    elif "downtrend" in content or "bearish trend" in content:
                        forex_data["trend"] = "down"
                    elif "sideways" in content or "range" in content:
                        forex_data["trend"] = "sideways"
                
                # Extract RSI values
                if "rsi" in content:
                    try:
                        # Try multiple formats of RSI representation
                        if ":" in content:
                            rsi_str = content.split("rsi:")[1].strip().split()[0].replace('%', '')
                        elif "=" in content:
                            rsi_str = content.split("rsi=")[1].strip().split()[0].replace('%', '')
                        else:
                            # Extract any number after RSI
                            rsi_match = re.search(r'rsi.*?(\d+\.?\d*)', content)
                            rsi_str = rsi_match.group(1) if rsi_match else None
                        
                        if rsi_str:
                            forex_data["indicators"]["RSI"] = float(rsi_str)
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.warning(f"Failed to parse RSI: {content} - Error: {e}")
                
                # Extract price levels
                price_mappings = {
                    "bid": "bid",
                    "ask": "ask",
                    "support": "support",
                    "resistance": "resistance",
                    "pivot": "pivot",
                    "s1": "support_1",
                    "s2": "support_2",
                    "r1": "resistance_1",
                    "r2": "resistance_2"
                }
                
                for term, key in price_mappings.items():
                    if term in content:
                        try:
                            # Extract price using regex to find numbers after the term
                            price_match = re.search(fr'{term}[^0-9]*(\d+\.?\d*)', content)
                            if price_match:
                                forex_data["price_levels"][key] = float(price_match.group(1))
                        except (ValueError, IndexError, AttributeError) as e:
                            logger.warning(f"Failed to parse {term}: {content} - Error: {e}")
            
            # Process bounding box data for spatial awareness
            if 'bbox' in item:
                bbox = item.get('bbox', {})
                # Use bounding box information to enhance context
                # For example, detecting chart areas vs indicator areas
                if bbox and all(k in bbox for k in ['x', 'y', 'width', 'height']):
                    # Top of screen typically contains price information
                    if bbox['y'] < 0.2:  # First 20% of screen height
                        if "price" in content or any(c.isdigit() for c in content):
                            # Try to extract a price from this area
                            price_match = re.search(r'(\d+\.\d+)', content)
                            if price_match:
                                forex_data["price_levels"]["current"] = float(price_match.group(1))
        
        # Determine overall market state from collected data
        if forex_data["indicators"].get("RSI", 50) > 70:
            forex_data["market_state"] = "overbought"
        elif forex_data["indicators"].get("RSI", 50) < 30:
            forex_data["market_state"] = "oversold"
        elif forex_data["trend"] == "up":
            forex_data["market_state"] = "bullish"
        elif forex_data["trend"] == "down":
            forex_data["market_state"] = "bearish"
        else:
            forex_data["market_state"] = "neutral"
        
        logger.info(f"Extracted Forex Data: {json.dumps(forex_data, default=str)}")
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

    def log_trade(self, trade: Dict[str, Any], market_data: Dict[str, Any], parsed_content_list: List[Dict[str, Any]], dino_labeled_img: str = "") -> None:
        """
        Log a trade to the trade history with enhanced OmniParser data.
        
        Args:
            trade: The trade decision
            market_data: The market data that led to the decision
            parsed_content_list: The raw OmniParser output
            dino_labeled_img: Base64-encoded labeled image from OmniParser
        """
        trade_log = {
            "timestamp": trade.get("timestamp", datetime.now().isoformat()),
            "currency_pair": self.currency_pair,
            "action": trade["action"],
            "reasoning": trade["reasoning"],
            "reward": trade["reward"],
            "market_data": market_data,
            "parsed_content_list": parsed_content_list,
            "dino_labeled_img": dino_labeled_img
        }
        
        self.trade_history.append(trade_log)
        logger.info(f"Trade logged: {trade['action']} at {trade_log['timestamp']}")
        
        # Optionally, you could save to a database or file here
        try:
            with open(f"{self.currency_pair}_trade_history.json", 'w') as f:
                # Save a version without the large base64 images for efficiency
                save_log = copy.deepcopy(trade_log)
                if save_log.get("dino_labeled_img"):
                    save_log["has_labeled_img"] = True
                    save_log["dino_labeled_img"] = "...base64 image removed for storage efficiency..."
                
                history_to_save = [log if not isinstance(log, dict) or not log.get("dino_labeled_img") 
                                 else {**log, "dino_labeled_img": "...base64 image removed..."}
                                 for log in self.trade_history]
                
                json.dump(history_to_save, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")

    def evaluate_performance(self) -> Dict[str, Any]:
        """
        Evaluate the trading performance based on trade history.
        
        Returns:
            Dict containing comprehensive performance metrics
        """
        if not self.trade_history:
            return {
                "win_rate": 0.0, 
                "total_trades": 0, 
                "active_trades": 0,
                "total_pips": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "strategy_performance": {}
            }
        
        # Count trades that are not "hold"
        trades = [t for t in self.trade_history if t["action"] != "hold"]
        total_trades = len(trades)
        
        if total_trades == 0:
            return {
                "win_rate": 0.0, 
                "total_trades": 0, 
                "active_trades": 0,
                "total_pips": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "strategy_performance": {}
            }
        
        # Calculate basic metrics
        wins = [t for t in trades if t.get("reward", 0) > 0]
        losses = [t for t in trades if t.get("reward", 0) < 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        
        win_rate = (win_count / total_trades * 100) if total_trades else 0.0
        
        # Calculate pip-based metrics
        total_pips = sum(t.get("reward", 0) for t in trades)
        total_win_pips = sum(t.get("reward", 0) for t in wins) if wins else 0
        total_loss_pips = abs(sum(t.get("reward", 0) for t in losses)) if losses else 0
        
        avg_win = total_win_pips / win_count if win_count else 0
        avg_loss = total_loss_pips / loss_count if loss_count else 0
        
        largest_win = max([t.get("reward", 0) for t in wins]) if wins else 0
        largest_loss = abs(min([t.get("reward", 0) for t in losses])) if losses else 0
        
        # Profit factor (ratio of gross profits to gross losses)
        profit_factor = total_win_pips / total_loss_pips if total_loss_pips > 0 else float('inf') if total_win_pips > 0 else 0
        
        # Calculate drawdown metrics
        cumulative_pips = [0]
        peak = 0
        drawdowns = []
        
        # Sort trades by timestamp
        sorted_trades = sorted(trades, key=lambda t: datetime.fromisoformat(t.get("timestamp", "2023-01-01T00:00:00")))
        
        # Calculate cumulative pips and track drawdowns
        for trade in sorted_trades:
            reward = trade.get("reward", 0)
            cumulative_pips.append(cumulative_pips[-1] + reward)
            
            # Update peak if we have a new high
            if cumulative_pips[-1] > peak:
                peak = cumulative_pips[-1]
            # Calculate current drawdown
            elif peak > 0:
                drawdown = (peak - cumulative_pips[-1]) / peak if peak > 0 else 0
                drawdowns.append(drawdown)
        
        max_drawdown = max(drawdowns) * 100 if drawdowns else 0  # As percentage
        
        # Calculate Sharpe ratio (simplified)
        if len(cumulative_pips) > 1:
            returns = [cumulative_pips[i] - cumulative_pips[i-1] for i in range(1, len(cumulative_pips))]
            avg_return = sum(returns) / len(returns)
            std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Calculate active trades
        active_trades = sum(1 for t in trades if t.get("status") == "open")
        
        # Calculate strategy performance
        strategy_performance = {}
        for trade in trades:
            strategies = trade.get("strategies_triggered", [])
            result = "win" if trade.get("reward", 0) > 0 else "loss" if trade.get("reward", 0) < 0 else "tie"
            
            for strategy in strategies:
                if strategy not in strategy_performance:
                    strategy_performance[strategy] = {"wins": 0, "losses": 0, "ties": 0, "total_pips": 0}
                
                if result == "win":
                    strategy_performance[strategy]["wins"] += 1
                elif result == "loss":
                    strategy_performance[strategy]["losses"] += 1
                else:
                    strategy_performance[strategy]["ties"] += 1
                
                strategy_performance[strategy]["total_pips"] += trade.get("reward", 0)
        
        # Calculate win rates for each strategy
        for strategy, data in strategy_performance.items():
            total = data["wins"] + data["losses"] + data["ties"]
            if total > 0:
                data["win_rate"] = (data["wins"] / total) * 100
            else:
                data["win_rate"] = 0
        
        # Final performance metrics
        performance = {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "active_trades": active_trades,
            "total_pips": total_pips,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "strategy_performance": strategy_performance,
            "last_trade_time": sorted_trades[-1].get("timestamp") if sorted_trades else None
        }
        
        logger.info(f"Performance evaluation: {json.dumps(performance, default=str)}")
        return performance

# Example usage:
# agent = TradingAgent(openai_api_key="your_key", omniparser_url="http://localhost:8000")
# market_data, parsed_content_list = agent.analyze_market(screenshot_base64)
# decision = agent.decide_trade(market_data)
# if decision["action"] != "hold":
#     # Execute trade
#     # ...
#     # Log trade
#     agent.log_performance(decision, profit=0.5)  # Profit in units of base currency 