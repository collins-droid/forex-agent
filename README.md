# Forex Trading Agent Chrome Extension

A Chrome extension that uses AI to automate Forex trading on the Exness platform by analyzing charts with OmniParser and making decisions with an LLM.

## Features

- 📊 Captures screenshots of Forex charts on Exness
- 🔍 Analyzes market data using OmniParser for perception
- 🧠 Uses GPT-4 to make trading decisions
- 💰 Executes trades directly on the Exness platform
- 📈 Logs performance and provides metrics

## Prerequisites

- Python 3.8+ (for the backend agent)
- Node.js and npm (optional, for development)
- Git (for version control)
- Chrome browser
- OmniParser service running locally or on a server

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/forex-trading-agent.git
cd forex-trading-agent
```

### 2. Set up the Python backend (optional)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install the Chrome extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top-right)
3. Click "Load unpacked" and select the `forex-trading-agent` folder
4. The extension should now appear in your Chrome toolbar

## Configuration

1. Click on the extension icon to open the popup
2. Enter your OpenAI API key
3. Configure OmniParser URL (default: `http://localhost:8000`)
4. Select your currency pair
5. Set polling interval and lot size
6. Configure DOM selectors for the Exness platform:
   - Buy button selector
   - Sell button selector
   - Chart selector

## Usage

1. Open the Exness trading platform in Chrome
2. Navigate to your chosen currency pair chart
3. Click the extension icon and configure settings
4. Click "Start Agent" to begin automated trading
5. The agent will:
   - Capture screenshots of the chart
   - Send them to OmniParser for analysis
   - Make trading decisions using GPT-4
   - Execute trades on your behalf
   - Track performance metrics

## Security and Risk Management

- API keys are stored securely in Chrome's extension storage
- Default to "Hold" position when uncertain
- The agent stops after repeated failures
- Always use a demo account for testing

## Disclaimer

This extension is for educational purposes only. Forex trading involves significant risk and you should never risk money you cannot afford to lose. The authors are not responsible for any financial losses incurred.

## License

MIT License 