Below is the updated refinement instruction set for your existing Forex trading Chrome extension within the `collins-droid-forex-agent/` structure.Follw These instructions to refine your current implementation by incorporating observations from the enhanced `TradingAgent` class, focusing on improving OmniParser integration, data extraction, error handling, and agentic capabilities. They assume you’ve already built the basic extension and aim to make it more robust and effective.
   


   the current directory structure is as follows:
    Current   Directory structure:
└── collins-droid-forex-agent/
    ├── changeLog.md
    ├── instructions.md
    ├── OmniPaser/
    │   ├── README.md
    │   ├── demo.ipynb
    │   ├── gradio_demo.py
    │   ├── requirements.txt
    │   ├── .gitignore
    │   ├── docs/
    │   │   └── Evaluation.md
    │   ├── eval/
    │   │   ├── logs_sspro_omniv2.json
    │   │   └── ss_pro_gpt4o_omniv2.py
    │   ├── imgs/
    │   ├── omnitool/
    │   │   ├── readme.md
    │   │   ├── gradio/
    │   │   │   ├── __init__.py
    │   │   │   ├── app.py
    │   │   │   ├── loop.py
    │   │   │   ├── .gitignore
    │   │   │   ├── agent/
    │   │   │   │   ├── anthropic_agent.py
    │   │   │   │   ├── vlm_agent.py
    │   │   │   │   └── llm_utils/
    │   │   │   │       ├── groqclient.py
    │   │   │   │       ├── oaiclient.py
    │   │   │   │       ├── omniparserclient.py
    │   │   │   │       └── utils.py
    │   │   │   ├── executor/
    │   │   │   │   └── anthropic_executor.py
    │   │   │   └── tools/
    │   │   │       ├── __init__.py
    │   │   │       ├── base.py
    │   │   │       ├── collection.py
    │   │   │       ├── computer.py
    │   │   │       └── screen_capture.py
    │   │   ├── omnibox/
    │   │   │   ├── Dockerfile
    │   │   │   ├── compose.yml
    │   │   │   ├── .gitignore
    │   │   │   ├── scripts/
    │   │   │   │   ├── manage_vm.ps1
    │   │   │   │   └── manage_vm.sh
    │   │   │   └── vm/
    │   │   │       ├── buildcontainer/
    │   │   │       │   ├── define.sh
    │   │   │       │   ├── entry.sh
    │   │   │       │   ├── install.sh
    │   │   │       │   ├── power.sh
    │   │   │       │   └── samba.sh
    │   │   │       ├── win11def/
    │   │   │       │   └── win11x64-enterprise-eval.xml
    │   │   │       ├── win11iso/
    │   │   │       │   └── README.md
    │   │   │       └── win11setup/
    │   │   │           ├── firstboot/
    │   │   │           │   └── install.bat
    │   │   │           └── setupscripts/
    │   │   │               ├── on-logon.ps1
    │   │   │               ├── setup-tools.psm1
    │   │   │               ├── setup.ps1
    │   │   │               ├── tools_config.json
    │   │   │               └── server/
    │   │   │                   ├── main.py
    │   │   │                   └── requirements.txt
    │   │   └── omniparserserver/
    │   │       └── omniparserserver.py
    │   └── util/
    │       ├── __init__.py
    │       ├── box_annotator.py
    │       ├── omniparser.py
    │       └── utils.py
    └── forex-trading-agent/
        ├── README.md
        ├── background.js
        ├── content.js
        ├── manifest.json
        ├── popup.html
        ├── popup.js
        └── backend/
            ├── requirements.txt
            ├── trading_agent.py
            └── utils.py

  ```

## Refinement Instructions for the Forex Trading Chrome Extension

**Goal**: Enhance the existing `forex-trading-agent` Chrome extension in `collins-droid-forex-agent/` to improve its AI agent capabilities, leveraging OmniParser for perception, refining LLM decision-making, adding robust logging, and enhancing user feedback, while maintaining your current setup.

---

### Instructions

#### 1. Enhance OmniParser Integration and Data Extraction
- **File**: `forex-trading-agent/backend/trading_agent.py`
  - **Action**: Refine `_extract_forex_data` for robust parsing of OmniParser output from `OmniParser/omnitool/omniparserserver/omniparserserver.py`.
  - **Steps**:
    - Test OmniParser with Exness screenshots at `http://localhost:8000/parse/` and log the `parsed_content_list` structure.
    - Update `_extract_forex_data` to:
      - Extract candlestick patterns (e.g., "bullish engulfing", "bearish engulfing") from text or image labels.
      - Parse RSI values robustly (e.g., handle "RSI: 25.5%" formats).
      - Add price levels (e.g., "Bid: 1.1234", "Resistance: 1.1300").
    - **Example**:
      ```python
      def _extract_forex_data(self, parsed_content_list):
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
          if not content: continue
          if "bullish engulfing" in content:
            forex_data["candlestick_patterns"].append("bullish_engulfing")
          elif "bearish engulfing" in content:
            forex_data["candlestick_patterns"].append("bearish_engulfing")
          elif "rsi" in content:
            try:
              rsi_str = content.split("rsi:")[1].strip().split()[0].replace('%', '')
              forex_data["indicators"]["RSI"] = float(rsi_str)
            except (ValueError, IndexError):
              logger.warning(f"Failed to parse RSI: {content}")
          elif "bid" in content:
            try:
              bid = float(content.split("bid:")[1].strip().split()[0])
              forex_data["price_levels"]["bid"] = bid
            except (ValueError, IndexError):
              logger.warning(f"Failed to parse bid: {content}")
          elif "resistance" in content:
            try:
              res = float(content.split("resistance:")[1].strip().split()[0])
              forex_data["price_levels"]["resistance"] = res
            except (ValueError, IndexError):
              logger.warning(f"Failed to parse resistance: {content}")
        logger.info(f"Extracted Forex Data: {forex_data}")
        return forex_data
      ```
    - Update `analyze_market` to return both `market_data` and `parsed_content_list`:
      ```python
      def analyze_market(self, screenshot_base64):
        try:
          response = self._call_omniparser(screenshot_base64)
          parsed_content_list = response.get('parsed_content_list', [])
          market_data = self._extract_forex_data(parsed_content_list)
          return market_data, parsed_content_list
        except Exception as e:
          logger.error(f"Market analysis error: {e}")
          raise
      ```
  - **Goal**: Improve perception accuracy and robustness.

#### 2. Refine LLM Decision-Making with Enhanced Prompting
- **File**: `forex-trading-agent/backend/trading_agent.py`
  - **Action**: Update `_construct_prompt` and `make_trade_decision` for strategic, context-aware reasoning.
  - **Steps**:
    - Enhance `_construct_prompt` to include trade history and explicit OmniParser reliance:
      ```python
      def _construct_prompt(self, market_data, currency_pair):
        history = self.trade_history[-3:] if self.trade_history else []
        history_str = json.dumps(history, indent=2) if history else "None"
        prompt = f"""
        You are a Forex trading AI for Exness on {currency_pair}.
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
      ```
    - Update `make_trade_decision` to enforce JSON output and handle errors:
      ```python
      def make_trade_decision(self, market_data, currency_pair):
        prompt = self._construct_prompt(market_data, currency_pair)
        try:
          response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
          )
          decision = json.loads(response.choices[0].message.content)
          decision["reward"] = 1 if decision["action"] in ["buy", "sell"] else 0
          return decision
        except Exception as e:
          logger.error(f"LLM error: {e}")
          return {"action": "hold", "reasoning": f"Error: {str(e)}", "reward": 0}
      ```
  - **Goal**: Boost decision quality with context and error resilience.

#### 3. Strengthen Trade Logging and Performance Tracking
- **File**: `forex-trading-agent/backend/trading_agent.py`
  - **Action**: Enhance `log_trade` and `evaluate_performance`.
  - **Steps**:
    - Update `log_trade` to include raw OmniParser data:
      ```python
      def log_trade(self, trade, market_data, parsed_content_list):
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
      ```
    - Refine `evaluate_performance` for basic metrics:
      ```python
      def evaluate_performance(self):
        if not self.trade_history:
          return {"win_rate": 0.0, "total_trades": 0}
        wins = sum(1 for t in self.trade_history if t["reward"] > 0 and t["action"] != "hold")
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total else 0.0
        return {"win_rate": win_rate, "total_trades": total}
      ```
  - **Goal**: Build a comprehensive memory system for analysis and refinement.

#### 4. Optimize Background Orchestration
- **File**: `forex-trading-agent/background.js`
  - **Action**: Refine `startTradingLoop` and `evaluatePerformance`.
  - **Steps**:
    - Update `startTradingLoop` to log parsed data and handle errors:
      ```javascript
      async function startTradingLoop() {
        const settings = await getTradingSettings();
        intervalId = setInterval(async () => {
          if (!agentRunning || errorCount >= 5) {
            if (errorCount >= 5) notifyUser("Agent Stopped", "Too many errors", true);
            return;
          }
          try {
            const screenshot = await captureTradingView();
            const decision = await getTradeDecision(screenshot, settings);
            tradeHistory.push({ ...decision, timestamp: new Date().toISOString() });
            if (decision.action !== "hold") {
              await executeTrade(decision.action, settings);
              notifyUser("Trade Executed", `${decision.action}: ${decision.reasoning}`);
            }
            evaluatePerformance();
            saveTradeHistory();
          } catch (error) {
            errorCount++;
            notifyUser("Error", error.message, true);
          }
        }, parseInt(settings.pollingInterval) || 15000);
      }
      ```
    - Enhance `evaluatePerformance`:
      ```javascript
      async function evaluatePerformance() {
        const recentTrades = tradeHistory.slice(-10);
        const winRate = recentTrades.filter(t => t.reward > 0).length / recentTrades.length * 100;
        chrome.runtime.sendMessage({ 
          message: "performance_update", 
          data: { winRate: winRate.toFixed(2), avgProfitLoss: "N/A" }
        });
        if (winRate < 40) notifyUser("Low Performance", "Win rate below 40%", true);
      }
      ```
  - **Goal**: Ensure smooth operation and user feedback.

#### 5. Improve DOM Interaction Resilience
- **File**: `forex-trading-agent/content.js`
  - **Action**: Enhance `executeTrade` with better error handling.
  - **Steps**:
    - Update:
      ```javascript
      async function executeTrade(decision, settings) {
        try {
          const quantityInput = queryElement(settings.quantityInputSelector || '#quantity-input', "Quantity Input");
          quantityInput.value = settings.lotSize || "0.01";
          const buttonSelector = decision === "buy" ? 
            (settings.buyButtonSelector || '#buy-btn') : 
            (settings.sellButtonSelector || '#sell-btn');
          const button = queryElement(buttonSelector, `${decision} Button`);
          button.click();
          return { success: true, profitLoss: "Pending" };
        } catch (error) {
          chrome.notifications.create({ type: "basic", title: "DOM Error", message: error.message });
          return { success: false, error: error.message };
        }
      }
      ```
  - **Goal**: Make trade execution fault-tolerant.

#### 6. Enhance User Interface Feedback
- **File**: `forex-trading-agent/popup.js`
  - **Action**: Improve performance display.
  - **Steps**:
    - Update:
      ```javascript
      chrome.runtime.onMessage.addListener(request => {
        if (request.message === "performance_update") {
          document.getElementById('winRate').textContent = request.data.winRate;
          document.getElementById('avgProfitLoss').textContent = request.data.avgProfitLoss;
        }
      });
      ```
  - **Goal**: Provide clear performance insights.

#### 7. Test and Optimize
- **Steps**:
  - Test OmniParser with Exness screenshots, refining `_extract_forex_data` based on `parsed_content_list`.
  - Run in Exness demo mode, logging trades to `trading_agent.log`.
  - Adjust LLM prompt and strategy based on performance data.
  - Verify DOM selectors align with Exness UI via inspection.

#### 8. Strengthen Security and Stability
- **Steps**:
  - Ensure API key is securely stored in `chrome.storage.sync`.
  - Maintain error limit (5) in `background.js`.
  - Enable logging in `trading_agent.py` to `trading_agent.log`.

---

### Refinement Checklist
1. OmniParser parsing refined with detailed `_extract_forex_data`.
2. LLM decisions improved with history and robust error handling.
3. Trade logging enhanced with raw OmniParser data.
4. Background loop optimized for reliability.
5. DOM interaction made resilient with notifications.
6. UI feedback improved for performance tracking.
7. Tested and optimized with Exness demo.
8. Security and stability reinforced with logging.



These refinements build on your existing `collins-droid-forex-agent/forex-trading-agent/` setup, incorporating robust data extraction, error handling, and agentic enhancements from the updated `TradingAgent` observations. Focus on testing `_extract_forex_data` and prompt tuning for optimal performance. Let me know if you need further refinements!