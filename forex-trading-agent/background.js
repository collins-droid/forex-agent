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
  const errorCount = {
    count: 0,
    maxErrors: 5
  };
  
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
    const omniparserResponse = await sendToOmniParser(settings.omniparserUrl, screenshotResult.image);
    const marketData = omniparserResponse.marketData;
    const parsedContentList = omniparserResponse.parsedContentList;
    
    // Log parsed data for debugging
    console.log(`OmniParser found ${parsedContentList.length} elements`);
    
    // 3 & 4. Analyze data with LLM and make trading decision
    console.log('Getting trading decision from LLM...');
    const tradingDecision = await getTradingDecision(settings.apiKey, marketData, parsedContentList, tradeHistory);
    
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
        lotSize: settings.lotSize || 0.01
      });
      
      // Merge trade result with decision
      tradingDecision.executionSuccess = tradeResult.success;
      tradingDecision.profitLoss = tradeResult.profitLoss;
      
      // Send notification to user
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon48.png',
        title: `Trade Executed: ${tradingDecision.action.toUpperCase()}`,
        message: tradingDecision.reasoning
      });
    } else {
      console.log('Decision: HOLD - No trade executed');
    }
    
    // 6. Log the trade
    logTrade({
      ...tradingDecision,
      timestamp: new Date().toISOString(),
      marketData: marketData,
      parsedContentList: parsedContentList
    });
    
    // 7. Update performance metrics
    evaluatePerformance();
    
    // Reset error count on success
    errorCount.count = 0;
    
  } catch (error) {
    console.error('Error in trading cycle:', error);
    
    // Increment error count
    errorCount.count++;
    
    // Handle the failure
    handleFailure(error);
    
    // Stop agent if too many consecutive errors
    if (errorCount.count >= errorCount.maxErrors) {
      console.error(`Stopping agent due to ${errorCount.count} consecutive errors`);
      stopAgent();
      
      // Notify user
      chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon48.png',
        title: 'Agent Stopped',
        message: `Trading agent stopped due to ${errorCount.count} consecutive errors`
      });
    }
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
 * @returns {Promise<Object>} - Parsed market data and raw parsed_content_list
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
    
    const omniparserResponse = await response.json();
    
    // Extract parsed_content_list from the response
    const parsed_content_list = omniparserResponse.parsed_content_list || [];
    
    // Log summary of parsed elements
    console.log(`OmniParser found ${parsed_content_list.length} elements in the image`);
    
    // Process the parsed content through the backend trading agent
    // This would normally be done by calling the trading agent's _extract_forex_data
    // But for simplicity, we'll mock the structure here
    const marketData = {
      currency_pair: "EURUSD", // This should come from settings
      timestamp: new Date().toISOString(),
      candlestick_patterns: [],
      indicators: {},
      price_levels: {},
      parsed_elements_count: parsed_content_list.length
    };
    
    // Return both the structured market data and the raw parsed_content_list
    return {
      marketData: marketData,
      parsedContentList: parsed_content_list
    };
  } catch (error) {
    console.error('OmniParser error:', error);
    throw new Error('Failed to parse chart: ' + error.message);
  }
}

/**
 * Gets trading decision from LLM
 * @param {string} apiKey - OpenAI API key
 * @param {Object} marketData - Structured market data
 * @param {Array} parsedContentList - Raw parsed content from OmniParser
 * @param {Array} history - Previous trade history
 * @returns {Promise<Object>} - Trading decision
 */
async function getTradingDecision(apiKey, marketData, parsedContentList, history) {
  try {
    // Create the prompt for the LLM
    const prompt = constructPrompt(marketData, parsedContentList, history);
    
    // Call OpenAI API
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.1,
        max_tokens: 200,
        response_format: { type: "json_object" }
      })
    });
    
    if (!response.ok) {
      throw new Error(`OpenAI API returned status ${response.status}`);
    }
    
    const result = await response.json();
    
    // Parse the decision
    let decision;
    try {
      decision = JSON.parse(result.choices[0].message.content);
    } catch (error) {
      console.error('Failed to parse LLM response as JSON', error);
      console.log('Raw response:', result.choices[0].message.content);
      throw new Error('Invalid response format from LLM');
    }
    
    // Validate decision format
    if (!decision.action || !decision.reasoning) {
      throw new Error('Invalid decision format from LLM');
    }
    
    // Normalize action to lowercase
    decision.action = decision.action.toLowerCase();
    
    // Ensure action is valid
    if (!['buy', 'sell', 'hold'].includes(decision.action)) {
      console.warn(`Invalid action '${decision.action}' from LLM, defaulting to 'hold'`);
      decision.action = 'hold';
    }
    
    // Add reward based on action (simple heuristic)
    decision.reward = decision.action !== 'hold' ? 1 : 0;
    
    return decision;
  } catch (error) {
    console.error('Trading decision error:', error);
    // Default to "hold" on error
    return {
      action: 'hold',
      reasoning: `Error getting trading decision: ${error.message}`,
      reward: 0
    };
  }
}

/**
 * Constructs prompt for the LLM
 * @param {Object} marketData - Structured market data
 * @param {Array} parsedContentList - Raw parsed content from OmniParser
 * @param {Array} history - Previous trade history
 * @returns {string} - Formatted prompt
 */
function constructPrompt(marketData, parsedContentList, history) {
  // Get recent trades history (up to 3 most recent trades)
  const recentTrades = history.slice(-3);
  const historyStr = JSON.stringify(recentTrades, null, 2) || "None";
  
  // Create a summary of parsed elements if there are many
  let parsedSummary = "";
  if (parsedContentList.length > 10) {
    const elementTypes = {};
    parsedContentList.forEach(item => {
      const type = item.type || "unknown";
      elementTypes[type] = (elementTypes[type] || 0) + 1;
    });
    
    parsedSummary = `\nSummary of parsed elements (${parsedContentList.length} total):\n`;
    for (const [type, count] of Object.entries(elementTypes)) {
      parsedSummary += `- ${type}: ${count}\n`;
    }
  }
  
  // Create a structured prompt
  return `
You are a Forex trading AI for Exness.

MARKET DATA (extracted from OmniParser):
\`\`\`json
${JSON.stringify(marketData, null, 2)}
\`\`\`

${parsedSummary}

RECENT TRADES:
\`\`\`json
${historyStr}
\`\`\`

TRADING STRATEGY:
- Buy if bullish engulfing pattern is present AND RSI < 30
- Sell if bearish engulfing pattern is present AND RSI > 70
- Hold if the signals are mixed or unclear

INSTRUCTIONS:
1. Analyze the market data step-by-step
2. Consider candlestick patterns and technical indicators
3. Use recent trade history to avoid repeated errors
4. Make a clear decision based on the strategy

Output ONLY a JSON object with:
{
  "action": "buy|sell|hold",
  "reasoning": "your step-by-step analysis and justification"
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