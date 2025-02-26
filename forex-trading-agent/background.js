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
    console.log('Sending to OmniParser for enhanced analysis...');
    const omniparserData = await sendToOmniParser(settings.omniparserUrl, screenshotResult.image);
    
    // Extract components from the enhanced OmniParser response
    const parsedContentList = omniparserData.parsed_content_list;
    const dinoLabeledImg = omniparserData.dino_labeled_img;
    const originalImage = omniparserData.original_image;
    
    // Check if we have an error from OmniParser
    if (omniparserData.error) {
      console.warn('OmniParser warning:', omniparserData.error);
      updateStatus('warning', `OmniParser warning: ${omniparserData.error}`);
    }
    
    // Log parsed data for debugging
    console.log(`OmniParser found ${parsedContentList.length} elements`);
    console.log(`Labeled image available: ${Boolean(dinoLabeledImg)}`);
    
    // 3. Send to backend for analysis
    console.log('Analyzing market data through backend API...');
    try {
      const apiResponse = await fetch(`http://localhost:5001/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          parsed_content_list: parsedContentList,
          original_image: originalImage,
          labeled_image: dinoLabeledImg,
          currency_pair: settings.currencyPair
        })
      });
      
      if (!apiResponse.ok) {
        throw new Error(`Backend API returned status ${apiResponse.status}`);
      }
      
      const analysisResult = await apiResponse.json();
      
      // Extract market data and trading decision
      const marketData = analysisResult.forex_data;
      const tradingDecision = analysisResult.trade_decision;
      
      // Check if we have sufficient data to make a decision
      if (!validateMarketData(marketData, parsedContentList)) {
        console.warn('Insufficient market data for reliable analysis');
        updateStatus('warning', 'Insufficient market data for reliable analysis');
        return;
      }
      
      // 4. Analyze data with LLM and make trading decision
      console.log('Getting trading decision from backend...');
      const adjustedDecision = await getTradingDecision(settings.apiKey, marketData, parsedContentList, tradeHistory, originalImage, dinoLabeledImg);
      
      // Log the decision details including triggered strategies
      console.log('Trading decision:', adjustedDecision);
      
      if (adjustedDecision.strategies_triggered && adjustedDecision.strategies_triggered.length > 0) {
        console.log('Strategies triggered:', adjustedDecision.strategies_triggered.join(', '));
      }
      
      // 5. Execute trade if needed
      if (adjustedDecision.action === 'open' && adjustedDecision.direction) {
        console.log(`Executing ${adjustedDecision.direction} trade...`);
        
        // Add stop loss and take profit if provided
        const stopLossPips = adjustedDecision.stop_loss_pips || settings.defaultStopLossPips || 15;
        const takeProfitPips = adjustedDecision.take_profit_pips || settings.defaultTakeProfitPips || 30;
        
        const tradeResult = await chrome.tabs.sendMessage(tab.id, {
          action: 'executeTrade',
          direction: adjustedDecision.direction,
          selectors: {
            buyButtonSelector: settings.buyButtonSelector,
            sellButtonSelector: settings.sellButtonSelector,
            lotSizeInputSelector: settings.lotSizeInputSelector,
            stopLossInputSelector: settings.stopLossInputSelector,
            takeProfitInputSelector: settings.takeProfitInputSelector
          },
          lotSize: (settings.lotSize || 0.01) * (adjustedDecision.position_size || 1.0),
          stopLossPips: stopLossPips,
          takeProfitPips: takeProfitPips
        });
        
        // Merge trade result with decision
        adjustedDecision.executionSuccess = tradeResult.success;
        adjustedDecision.profitLoss = tradeResult.profitLoss;
        adjustedDecision.openPrice = tradeResult.openPrice;
        
        // Send notification to user with more detailed analysis
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icon48.png',
          title: `Trade Executed: ${adjustedDecision.direction.toUpperCase()}`,
          message: `${adjustedDecision.reasoning[0] || 'Based on market analysis'} | SL: ${stopLossPips} pips, TP: ${takeProfitPips} pips`
        });
        
        // Update status with the execution details
        updateStatus('success', `Executed ${adjustedDecision.direction} trade with ${(settings.lotSize * adjustedDecision.position_size).toFixed(2)} lots`);
      } else {
        console.log('Decision: HOLD - No trade executed');
        updateStatus('info', 'Analysis complete: No trade executed');
      }
      
      // 6. Log the trade with enhanced data
      logTrade({
        ...adjustedDecision,
        timestamp: new Date().toISOString(),
        marketData: marketData,
        parsedContentList: parsedContentList,
        analysisType: 'multi-strategy',
        originalDecision: tradingDecision
      });
      
      // 7. Update performance metrics with enhanced evaluation
      evaluatePerformance();
      
      // Reset error count on success
      errorCount.count = 0;
      
    } catch (error) {
      console.error('Error in trading cycle:', error);
      
      // Increment error count
      errorCount.count++;
      
      // Handle the failure with better error reporting
      handleFailure(error);
      
      if (errorCount.count >= errorCount.maxErrors) {
        console.error(`Reached maximum error count (${errorCount.maxErrors}), stopping agent`);
        stopAgent();
        updateStatus('error', `Stopped due to repeated errors: ${error.message}`);
      }
    }
  } catch (error) {
    console.error('Error in trading cycle:', error);
    
    // Increment error count
    errorCount.count++;
    
    // Handle the failure with better error reporting
    handleFailure(error);
    
    if (errorCount.count >= errorCount.maxErrors) {
      console.error(`Reached maximum error count (${errorCount.maxErrors}), stopping agent`);
      stopAgent();
      updateStatus('error', `Stopped due to repeated errors: ${error.message}`);
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
      'lotSizeInputSelector',
      'defaultStopLossPips',
      'defaultTakeProfitPips',
      'stopLossInputSelector',
      'takeProfitInputSelector'
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
    console.log('Sending screenshot to OmniParser with enhanced parameters');
    
    const response = await fetch(`${omniparserUrl}/parse/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        base64_image: base64Image,
        focus: "forex_chart",
        box_threshold: 0.05,
        iou_threshold: 0.1
      })
    });
    
    if (!response.ok) {
      throw new Error(`OmniParser returned status ${response.status}`);
    }
    
    const omniparserResponse = await response.json();
    
    // Extract data from the enhanced response
    const parsed_content_list = omniparserResponse.parsed_content_list || [];
    const dino_labeled_img = omniparserResponse.dino_labeled_img || '';
    
    // Log summary of parsed elements
    console.log(`OmniParser found ${parsed_content_list.length} elements in the image`);
    
    // Check if we have a labeled image
    console.log(`Labeled image available: ${Boolean(dino_labeled_img)}`);
    
    return {
      parsed_content_list,
      dino_labeled_img,
      original_image: base64Image
    };
  } catch (error) {
    console.error('OmniParser error:', error);
    // Return minimal structure on error
    return {
      parsed_content_list: [],
      dino_labeled_img: '',
      original_image: base64Image,
      error: error.message
    };
  }
}

/**
 * Get a trading decision from the backend trading agent
 * @param {string} apiKey - OpenAI API key
 * @param {Object} marketData - Extracted forex market data
 * @param {Array} parsedContentList - Raw parsed elements from OmniParser
 * @param {Array} history - Trade history
 * @param {string} originalImage - Base64 original chart image
 * @param {string} labeledImage - Base64 DINO labeled image
 * @returns {Promise<Object>} - Trading decision
 */
async function getTradingDecision(apiKey, marketData, parsedContentList, history, originalImage = '', labeledImage = '') {
  try {
    // Prepare the input data
    const currencyPair = marketData.currency_pair || 'EURUSD';
    
    // Create the request body with enhanced dual-image support
    const requestData = {
      market_data: marketData,
      parsed_content_list: parsedContentList,
      trade_history: history,
      original_image: originalImage,
      labeled_image: labeledImage,
      settings: {
        api_key: apiKey,
        currency_pair: currencyPair,
        use_multi_strategy: true,
        use_dual_image: Boolean(labeledImage)
      }
    };
    
    // Log request details for debugging
    console.log('Trading decision request:');
    console.log('- Market data fields:', Object.keys(marketData));
    console.log('- Parsed elements:', parsedContentList.length);
    console.log('- Using dual-image approach:', Boolean(labeledImage));
    console.log('- Historical trades:', history.length);
    
    // Call the backend API (with enhanced error handling)
    console.log('Calling backend trading agent with enhanced parameters...');
    
    let decision;
    
    try {
      // Try to call local backend
      const backendUrl = await getBackendUrl();
      
      console.log(`Connecting to backend at ${backendUrl}/analyze...`);
      
      const response = await fetch(`${backendUrl}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData),
        timeout: 15000  // 15 second timeout for image processing
      });
      
      if (!response.ok) {
        throw new Error(`Backend API returned status ${response.status}`);
      }
      
      const result = await response.json();
      decision = result.trade_decision;
      
      // Additional fields from enhanced backend
      const confidenceMetrics = result.confidence_metrics || {};
      const strategySignals = result.strategy_signals || {};
      
      console.log('Backend returned decision', decision);
      console.log('Strategy signals:', strategySignals);
      console.log('Confidence metrics:', confidenceMetrics);
      
      // Add the additional metrics to the decision
      decision.confidence_metrics = confidenceMetrics;
      decision.strategy_signals = strategySignals;
      
    } catch (backendError) {
      console.warn('Backend call failed, falling back to OpenAI API', backendError);
      
      // Fall back to OpenAI with dual-image approach if available
      const prompt = constructPrompt(marketData, parsedContentList, history, 
                                    Boolean(labeledImage) && Boolean(originalImage));
      
      const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-4-vision-preview',
          messages: [
            {
              role: 'system',
              content: 'You are a sophisticated forex trading assistant that analyzes market data and makes trading decisions. Respond with JSON only.'
            },
            {
              role: 'user',
              content: [
                { type: 'text', text: prompt }
              ].concat(originalImage ? [
                { 
                  type: 'image_url', 
                  image_url: { url: `data:image/png;base64,${originalImage}` } 
                }
              ] : []).concat(labeledImage ? [
                { 
                  type: 'image_url', 
                  image_url: { url: `data:image/png;base64,${labeledImage}` } 
                }
              ] : [])
            }
          ],
          temperature: 0.1,
          max_tokens: 1000,
          response_format: { type: "json_object" }
        })
      });
      
      if (!openaiResponse.ok) {
        throw new Error(`OpenAI API returned status ${openaiResponse.status}`);
      }
      
      const openaiResult = await openaiResponse.json();
      
      try {
        decision = JSON.parse(openaiResult.choices[0].message.content);
      } catch (parseError) {
        console.error('Failed to parse LLM response as JSON', parseError);
        console.log('Raw response:', openaiResult.choices[0].message.content);
        throw new Error('Invalid response format from LLM');
      }
    }
    
    // Validate and normalize decision
    if (!decision || typeof decision !== 'object') {
      throw new Error('Invalid decision format: missing decision object');
    }
    
    // Normalize action field ('buy'/'sell' -> 'open' with direction)
    if (decision.action === 'buy' || decision.action === 'sell') {
      decision.direction = decision.action;
      decision.action = 'open';
    } else if (decision.action === 'hold') {
      decision.direction = null;
    }
    
    // Normalize action to string
    decision.action = String(decision.action || 'hold').toLowerCase();
    
    // Ensure we have an array for reasoning
    if (typeof decision.reasoning === 'string') {
      decision.reasoning = [decision.reasoning];
    } else if (!Array.isArray(decision.reasoning)) {
      decision.reasoning = [];
    }
    
    // Set a default confidence value if not present
    if (typeof decision.confidence !== 'number') {
      decision.confidence = 0.5;
    }
    
    // Validate stop loss and take profit values
    if (decision.stop_loss_pips && !isNaN(Number(decision.stop_loss_pips))) {
      decision.stop_loss_pips = Number(decision.stop_loss_pips);
    }
    
    if (decision.take_profit_pips && !isNaN(Number(decision.take_profit_pips))) {
      decision.take_profit_pips = Number(decision.take_profit_pips);
    }
    
    // Add a timestamp
    decision.timestamp = new Date().toISOString();
    
    return decision;
    
  } catch (error) {
    console.error('Error getting trading decision:', error);
    
    // Return a safe default decision
    return {
      action: 'hold',
      direction: null,
      confidence: 0,
      reasoning: [`Error getting trading decision: ${error.message}`],
      timestamp: new Date().toISOString()
    };
  }
}

/**
 * Get the backend URL from settings or use default
 */
async function getBackendUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get('backendUrl', function(data) {
      resolve(data.backendUrl || 'http://localhost:5000');
    });
  });
}

/**
 * Constructs a detailed prompt for the LLM based on market data and trade history
 */
function constructPrompt(marketData, parsedContentList, history, useDualImage) {
  // Get recent trades history (up to 5 most recent trades)
  const recentTrades = history.slice(-5);
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
  
  // Calculate current performance metrics
  let performanceStr = "No previous trades";
  if (recentTrades.length > 0) {
    const wins = recentTrades.filter(t => t.profitLoss > 0).length;
    const winRate = recentTrades.length > 0 ? (wins / recentTrades.length * 100).toFixed(1) : 0;
    performanceStr = `Win rate: ${winRate}% (${wins}/${recentTrades.length} trades)`;
  }
  
  // Add dual-image specific instructions if using the vision model
  let dualImageInstructions = "";
  if (useDualImage) {
    dualImageInstructions = `
DUAL-IMAGE ANALYSIS INSTRUCTIONS:
You are provided with two images:
1. The original chart image showing the forex trading interface
2. A DINO-labeled image with detected objects and text highlighted

When analyzing these images:
- The original image gives you context and visual patterns
- The labeled image highlights detected price levels, indicators, and text
- Pay special attention to areas highlighted in the labeled image
- Identify candlestick patterns, trend lines, and support/resistance levels
- Look for indicator values (RSI, MACD, etc.) in both images
- Compare visual patterns with the extracted data in the market data JSON
`;
  }
  
  // Create a structured prompt with multiple trading strategies
  return `
You are an expert Forex trading AI using a multi-strategy approach${useDualImage ? ' with dual-image analysis capabilities' : ''}.

MARKET DATA (extracted from OmniParser):
\`\`\`json
${JSON.stringify(marketData, null, 2)}
\`\`\`

${parsedSummary}

RECENT TRADES:
\`\`\`json
${historyStr}
\`\`\`

PERFORMANCE: ${performanceStr}
${dualImageInstructions}
AVAILABLE TRADING STRATEGIES:
1. Trend Following
   - Buy in uptrends confirmed by positive MACD
   - Sell in downtrends confirmed by negative MACD
   - Look for aligned moving averages (20 EMA > 50 EMA for uptrends)

2. Breakout Strategy
   - Buy on confirmed resistance breakouts
   - Sell on confirmed support breakdowns
   - Require volume confirmation when possible
   - Look for price exceeding previous swing highs/lows

3. Mean Reversion
   - Buy when RSI < 30 (oversold) and price near support
   - Sell when RSI > 70 (overbought) and price near resistance
   - Check Bollinger Band compression and expansion

4. Pattern Recognition
   - Buy on bullish patterns (engulfing, hammer, morning star)
   - Sell on bearish patterns (engulfing, shooting star, evening star)
   - Validate patterns with volume and location (support/resistance)

5. Multi-Timeframe Analysis
   - Confirm signals across multiple indicators
   - Ensure alignment of short and medium-term trends
   - Look for confluence of signals (multiple indicators agreeing)

RISK MANAGEMENT RULES:
- Apply tighter stop-loss in high volatility conditions
- Reduce position size after consecutive losses (0.5x after 2+ losses)
- Increase position size gradually during successful streaks (max 1.5x)
- Use ATR for stop-loss calculation (1.5-2x ATR for stop-loss distance)
- Set risk-reward ratio minimum of 1:1.5, preferably 1:2 or higher
- Maximum risk per trade: 2% of account balance

ANALYSIS INSTRUCTIONS:
1. Evaluate each strategy separately
2. Identify which strategies are triggering signals
3. Check for confirming/conflicting signals between strategies
4. Apply risk management rules
5. Provide specific values for stop-loss and take-profit
6. Calculate position size based on risk parameters
7. Include confidence score based on signal strength and confluence

${useDualImage ? `IMAGE ANALYSIS:
Analyze both provided images carefully. Use the original image for context and pattern recognition, and the labeled image to identify key elements highlighted by the DINO detector. Incorporate visual cues into your decision-making process.
` : ''}

REQUIRED OUTPUT FORMAT (JSON):
{
  "action": "open" or "hold",
  "direction": "buy" or "sell" or null,
  "confidence": number from 0.0 to 1.0,
  "reasoning": ["reason1", "reason2", ...],
  "strategies_triggered": ["strategy1", "strategy2", ...],
  "stop_loss_pips": number,
  "take_profit_pips": number,
  "position_size": number,
  "market_conditions": {
    "trend": "bullish", "bearish", or "sideways",
    "volatility": "high", "normal", or "low",
    "key_levels": ["level1", "level2", ...]
  }
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

/**
 * Validates that market data has sufficient information for decision-making
 */
function validateMarketData(marketData, parsedContentList) {
  // Check if we have the minimum required data
  if (!marketData || !parsedContentList || parsedContentList.length < 3) {
    console.warn('Insufficient parsed content in market data');
    return false;
  }
  
  // Check for minimum required fields in marketData
  const requiredFields = ['currency_pair', 'indicators', 'price_levels', 'candlestick_patterns'];
  const missingFields = requiredFields.filter(field => !marketData[field]);
  
  if (missingFields.length > 0) {
    console.warn(`Market data missing required fields: ${missingFields.join(', ')}`);
    return false;
  }
  
  // Check for price data (minimum bid/ask)
  if (!marketData.price_levels || (!marketData.price_levels.bid && !marketData.price_levels.ask)) {
    console.warn('No price data (bid/ask) available in market data');
    return false;
  }
  
  return true;
}

/**
 * Applies additional risk management rules based on recent performance
 */
function applyRiskManagement(decision, performance) {
  // Create a copy to avoid modifying the original
  const adjustedDecision = {...decision};
  
  // Don't adjust if we're holding
  if (decision.action !== 'open' || !decision.direction) {
    return adjustedDecision;
  }
  
  // Adjust position size based on win rate
  if (performance.totalTrades > 10) {
    if (performance.winRate < 40) {
      // Poor performance, reduce position size
      adjustedDecision.position_size = (decision.position_size || 1.0) * 0.5;
      adjustedDecision.reasoning.push('Position size reduced due to poor win rate');
    } else if (performance.winRate > 60) {
      // Good performance, slightly increase position size
      adjustedDecision.position_size = (decision.position_size || 1.0) * 1.2;
      adjustedDecision.reasoning.push('Position size increased due to good win rate');
    }
  }
  
  // Check for losing streak (basic implementation)
  if (tradeHistory.length >= 3) {
    const recentTrades = tradeHistory.slice(-3);
    const recentLosses = recentTrades.filter(t => t.profitLoss < 0).length;
    
    if (recentLosses === 3) {
      // Three consecutive losses, be more conservative
      adjustedDecision.position_size = (decision.position_size || 1.0) * 0.5;
      
      // If the confidence is low, don't trade at all
      if ((decision.confidence || 0.5) < 0.7) {
        adjustedDecision.action = 'hold';
        adjustedDecision.direction = null;
        adjustedDecision.reasoning.push('Trade aborted due to consecutive losses and low confidence');
      } else {
        adjustedDecision.reasoning.push('Position size reduced due to consecutive losses');
      }
    }
  }
  
  // Check for volatility (assuming we have some measure in the market data)
  if (decision.marketData && decision.marketData.indicators && decision.marketData.indicators.ATR) {
    const atr = decision.marketData.indicators.ATR;
    if (typeof atr === 'number' && atr > 20) {  // High ATR threshold
      adjustedDecision.position_size = (decision.position_size || 1.0) * 0.7;
      adjustedDecision.reasoning.push('Position size reduced due to high volatility');
    }
  }
  
  // Ensure position size stays within reasonable bounds
  adjustedDecision.position_size = Math.max(0.1, Math.min(2.0, adjustedDecision.position_size || 1.0));
  
  return adjustedDecision;
}

/**
 * Updates the agent status and reports to popup
 */
function updateStatus(type, message) {
  const status = { type, message, timestamp: new Date().toISOString() };
  chrome.storage.local.set({ agentStatus: status });
  
  // Also send a message to any open popup
  chrome.runtime.sendMessage({ 
    action: 'statusUpdate',
    status
  }).catch(() => {
    // Popup may not be open, this is fine
  });
} 