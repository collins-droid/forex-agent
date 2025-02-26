#### 1. Set Up the Development Environment
- Install Python 3.8+ for the backend agent.
- Install Node.js and npm for JavaScript dependencies (optional).
- Install Git for version control.
- Create a project directory: `mkdir forex-trading-agent && cd forex-trading-agent`.
- Initialize a Git repository: `git init`.
- Set up a Python virtual environment: `python -m venv venv`.
- Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows).

#### 2. Build the Chrome Extension Structure
- Create the following directory structure:
  ```
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
- In `manifest.json`, use Manifest V3 with:
  - Permissions: `"activeTab"`, `"storage"`, `"scripting"`, `"unlimitedStorage"`.
  - Host permissions: `"*://*.exness.com/*"`.
  - Define popup (`popup.html`), background script (`background.js`), and content script (`content.js`).
- In `popup.html` and `popup.js`, create a UI for:
  - Settings: API key, OmniParser URL, currency pair, polling interval, lot size, DOM mappings.
  - Buttons: Start/stop agent, display metrics (win rate, P/L).
- In `content.js`:
  - Capture Exness chart screenshots using `html2canvas`.
  - Execute trades via DOM manipulation (e.g., click buy/sell buttons).
- In `background.js`:
  - Run the trading loop: capture screenshots, call OmniParser, get LLM decisions, execute trades, log results.
  - Track performance and send user notifications.

#### 3. Integrate OmniParser for Perception
- Set up OmniParser on a server (e.g., `http://localhost:8000`).
- Test the `/parse/` endpoint with a base64-encoded screenshot to confirm structured data output.
- In `trading_agent.py`:
  - Add an `analyze_market()` method in the `TradingAgent` class to send screenshots to OmniParser.
  - Add `_extract_forex_data()` to parse OmniParser output for candlesticks and indicators.
- Update the LLM prompt in `_construct_prompt()` to:
  - Use OmniParser data for decisions.
  - Include trade history for context.

#### 4. Implement Decision-Making Logic
- In `trading_agent.py`:
  - Define a `TradingAgent` class with methods: `analyze_market()`, `decide_trade()`, `log_performance()`.
  - Use OpenAI’s API (or another LLM) to process data and return JSON trade decisions.
- In the LLM prompt:
  - Instruct it to interpret OmniParser data and apply a simple trading strategy (e.g., trend-following).
  - Emphasize risk management and OmniParser reliance.
- In `content.js`:
  - Implement DOM manipulation to execute buy/sell trades based on decisions.
  - Use user-defined DOM mappings for flexibility.

#### 5. Add Memory and Learning
- In `trading_agent.py`:
  - Log trade details (action, reasoning, reward, market data) in `log_performance()`.
- In `background.js`:
  - Store trade history in `chrome.storage.local`.
- In `background.js`, add `evaluatePerformance()` to:
  - Calculate win rate and average P/L.
  - Notify users of performance trends.
- In `popup.js`:
  - Display metrics in the UI.
  - Allow users to tweak settings (e.g., lot size, strategy).

#### 6. Test and Refine
- Backtest with historical Exness screenshots to validate logic.
- Test live in an Exness demo account, monitoring decisions and performance.
- Refine the LLM prompt and strategy based on results to improve accuracy and risk-reward balance.

#### 7. Ensure Security and Ethics
- Store API keys in `chrome.storage.sync`, not in logs/UI.
- Add a disclaimer in `popup.html`: "For educational use only; trading involves risk."
- Add fail-safes:
  - Stop the agent after repeated failures (e.g., 5 losses).
  - Default to "hold" when uncertain.


