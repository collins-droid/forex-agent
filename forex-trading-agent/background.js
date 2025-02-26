// Background service worker for the Forex Trading Agent
console.log('Forex Trading Agent: background script loaded');

// Agent state
let agentRunning = false;
let agentIntervalId = null;
let tradeHistory = [];
let tradePerformance = {
  winRate: 0,
  profitLoss: 0,
  totalTrades: 0
};

// Load previous state if available
chrome.storage.local.get(['agentRunning', 'tradeHistory', 'tradePerformance'], function(data) {
  if (data.agentRunning) {
    startAgent();
  }
  
  if (data.tradeHistory) {
    tradeHistory = data.tradeHistory;
  }
  
  if (data.tradePerformance) {
    tradePerformance = data.tradePerformance;
  }
});

// Listen for messages from popup or content script
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log('Background script received message:', request);
  
  switch(request.action) {
    case 'startAgent':
      startAgent();
      sendResponse({ success: true });
      break;
      
    case 'stopAgent':
      stopAgent();
      sendResponse({ success: true });
      break;
      
    case 'getAgentStatus':
      sendResponse({
        agentRunning,
        tradePerformance
      });
      break;
  }
});

/**
 * Starts the trading agent
 */
function startAgent() {
  if (agentRunning) return;
  
  agentRunning = true;
  chrome.storage.local.set({ agentRunning });
  
  console.log('Starting trading agent...');
  
  // Run the trading loop immediately once
  runTradingCycle();
  
  // Then set up the interval
  chrome.storage.sync.get('pollingInterval', function(data) {
    const intervalSeconds = data.pollingInterval || 30;
    agentIntervalId = setInterval(runTradingCycle, intervalSeconds * 1000);
  });
}

/**
 * Stops the trading agent
 */
function stopAgent() {
  if (!agentRunning) return;
  
  agentRunning = false;
  chrome.storage.local.set({ agentRunning });
  
  if (agentIntervalId) {
    clearInterval(agentIntervalId);
    agentIntervalId = null;
  }
  
  console.log('Trading agent stopped');
}

/**
 * Executes a single trading cycle:
 * 1. Capture screenshot
 * 2. Send to OmniParser
 * 3. Analyze data with LLM
 * 4. Make trading decision
 * 5. Execute trade if needed
 * 6. Log results
 */
async function runTradingCycle() {
  try {
    console.log('Running trading cycle...');
    
    // Get settings
    const settings = await getSettings();
    
    // Get active tab on Exness
    const tabs = await chrome.tabs.query({
      active: true,
      url: '*://*.exness.com/*'
    });
    
    if (tabs.length === 0) {
      console.warn('No active Exness tab found');
      return;
    }
    
    const tab = tabs[0];
    
    // 1. Capture screenshot
    console.log('Capturing screenshot...');
    const screenshotResult = await chrome.tabs.sendMessage(tab.id, {
      action: 'captureScreenshot',
      chartSelector: settings.chartSelector
    });
    
    if (!screenshotResult.success) {
      throw new Error('Failed to capture screenshot: ' + screenshotResult.error);
    }
    
    // 2. Send to OmniParser
    console.log('Sending to OmniParser...');
    const marketData = await sendToOmniParser(settings.omniparserUrl, screenshotResult.image);
    
    // 3 & 4. Analyze data with LLM and make trading decision
    console.log('Getting trading decision from LLM...');
    const tradingDecision = await getTradingDecision(settings.apiKey, marketData, tradeHistory);
    
    // 5. Execute trade if needed
    if (tradingDecision.action !== 'hold') {
      console.log(`Executing ${tradingDecision.action} trade...`);
      
      const tradeResult = await chrome.tabs.sendMessage(tab.id, {
        action: 'executeTrade',
        direction: tradingDecision.action,
        selectors: {
          buyButtonSelector: settings.buyButtonSelector,
          sellButtonSelector: settings.sellButtonSelector,
          lotSizeInputSelector: settings.lotSizeInputSelector
        },
        lotSize: settings.lotSize
      });
      
      if (!tradeResult.success) {
        throw new Error('Failed to execute trade: ' + tradeResult.error);
      }
      
      // 6. Log results
      const trade = {
        timestamp: new Date().toISOString(),
        action: tradingDecision.action,
        reasoning: tradingDecision.reasoning,
        marketData: marketData,
        result: tradeResult.result,
        profit: null // To be updated later
      };
      
      logTrade(trade);
    } else {
      console.log('Decision: Hold position, no trade executed');
    }
    
    // Update performance metrics
    evaluatePerformance();
    
  } catch (error) {
    console.error('Trading cycle error:', error);
    
    // Handle consecutive failures
    handleFailure(error);
  }
}

/**
 * Gets all required settings from storage
 * @returns {Promise<Object>} - Settings object
 */
function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([
      'apiKey',
      'omniparserUrl',
      'currencyPair',
      'pollingInterval',
      'lotSize',
      'buyButtonSelector',
      'sellButtonSelector',
      'chartSelector',
      'lotSizeInputSelector'
    ], function(settings) {
      resolve(settings);
    });
  });
}

/**
 * Sends screenshot to OmniParser for analysis
 * @param {string} omniparserUrl - URL of OmniParser API
 * @param {string} base64Image - Base64-encoded screenshot
 * @returns {Promise<Object>} - Parsed market data
 */
async function sendToOmniParser(omniparserUrl, base64Image) {
  try {
    const response = await fetch(`${omniparserUrl}/parse/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        image: base64Image
      })
    });
    
    if (!response.ok) {
      throw new Error(`OmniParser returned status ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('OmniParser error:', error);
    throw new Error('Failed to parse chart: ' + error.message);
  }
}

/**
 * Gets trading decision from LLM
 * @param {string} apiKey - OpenAI API key
 * @param {Object} marketData - Data from OmniParser
 * @param {Array} history - Previous trade history
 * @returns {Promise<Object>} - Trading decision
 */
async function getTradingDecision(apiKey, marketData, history) {
  try {
    const prompt = constructPrompt(marketData, history);
    
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4',
        messages: [
          {
            role: 'system',
            content: 'You are an expert forex trading assistant. Analyze the market data and provide trading advice in JSON format with action and reasoning fields.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3,
        response_format: { type: 'json_object' }
      })
    });
    
    if (!response.ok) {
      throw new Error(`OpenAI API returned status ${response.status}`);
    }
    
    const result = await response.json();
    const decision = JSON.parse(result.choices[0].message.content);
    
    // Validate decision format
    if (!decision.action || !decision.reasoning) {
      throw new Error('Invalid decision format from LLM');
    }
    
    // Ensure action is one of: buy, sell, hold
    if (!['buy', 'sell', 'hold'].includes(decision.action)) {
      console.warn(`Invalid action "${decision.action}" from LLM, defaulting to "hold"`);
      decision.action = 'hold';
    }
    
    return decision;
  } catch (error) {
    console.error('LLM decision error:', error);
    // Default to "hold" when there's an error
    return {
      action: 'hold',
      reasoning: 'Error getting trading decision: ' + error.message
    };
  }
}

/**
 * Constructs prompt for the LLM
 * @param {Object} marketData - Data from OmniParser
 * @param {Array} history - Previous trade history
 * @returns {string} - Formatted prompt
 */
function constructPrompt(marketData, history) {
  // Recent trade history (up to 5 most recent trades)
  const recentTrades = history.slice(-5).map((trade, index) => {
    return `Trade ${index + 1}: ${trade.action.toUpperCase()} at ${new Date(trade.timestamp).toLocaleString()} - Reasoning: ${trade.reasoning}`;
  }).join('\n');
  
  return `
Please analyze this forex market data and make a trading decision.

MARKET DATA:
${JSON.stringify(marketData, null, 2)}

RECENT TRADE HISTORY:
${recentTrades || 'No previous trades'}

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
`;
}

/**
 * Logs a trade to history
 * @param {Object} trade - Trade details
 */
function logTrade(trade) {
  tradeHistory.push(trade);
  
  // Keep only the last 100 trades to avoid excessive storage
  if (tradeHistory.length > 100) {
    tradeHistory = tradeHistory.slice(-100);
  }
  
  // Save to storage
  chrome.storage.local.set({ tradeHistory });
  
  console.log('Trade logged:', trade);
}

/**
 * Evaluates trading performance
 */
function evaluatePerformance() {
  // For a real implementation, this would analyze actual P/L
  // Here we're using a simplified demonstration
  
  // Count wins and losses (in a real scenario, this would use actual P/L values)
  let wins = 0;
  let totalPL = 0;
  
  tradeHistory.forEach(trade => {
    // In a real implementation, trade.profit would be populated
    // For demo purposes, randomly assign profits/losses
    if (trade.profit === null) {
      // Mock profit/loss (would be real in production)
      const mockPL = (Math.random() > 0.5) ? 
        Math.random() * 10 : 
        -Math.random() * 8;
        
      trade.profit = mockPL;
      
      if (mockPL > 0) wins++;
      totalPL += mockPL;
    } else {
      if (trade.profit > 0) wins++;
      totalPL += trade.profit;
    }
  });
  
  // Calculate metrics
  tradePerformance = {
    winRate: tradeHistory.length > 0 ? (wins / tradeHistory.length) * 100 : 0,
    profitLoss: totalPL,
    totalTrades: tradeHistory.length
  };
  
  // Save to storage
  chrome.storage.local.set({ tradePerformance });
  
  // Update UI if popup is open
  chrome.runtime.sendMessage({
    action: 'updateMetrics',
    ...tradePerformance
  });
  
  console.log('Performance metrics updated:', tradePerformance);
}

/**
 * Handles consecutive failures
 * @param {Error} error - The error that occurred
 */
function handleFailure(error) {
  // This is a simplified version
  // In a real implementation, you would track consecutive failures
  // and stop the agent if too many occur
  
  console.warn('Trading cycle failed:', error.message);
  
  // Check for critical errors that should stop the agent
  const criticalErrors = [
    'API key invalid',
    'Account balance too low',
    'Connection to broker lost'
  ];
  
  for (const criticalError of criticalErrors) {
    if (error.message.includes(criticalError)) {
      console.error('Critical error detected, stopping agent:', error.message);
      stopAgent();
      
      // Notify user
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon.png',
        title: 'Trading Agent Stopped',
        message: `Agent stopped due to critical error: ${error.message}`
      });
      
      break;
    }
  }
} 