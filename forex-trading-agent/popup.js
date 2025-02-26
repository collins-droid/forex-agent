document.addEventListener('DOMContentLoaded', function() {
  // DOM elements
  const apiKeyInput = document.getElementById('apiKey');
  const omniparserUrlInput = document.getElementById('omniparserUrl');
  const currencyPairSelect = document.getElementById('currencyPair');
  const pollingIntervalInput = document.getElementById('pollingInterval');
  const lotSizeInput = document.getElementById('lotSize');
  const buyButtonSelectorInput = document.getElementById('buyButtonSelector');
  const sellButtonSelectorInput = document.getElementById('sellButtonSelector');
  const chartSelectorInput = document.getElementById('chartSelector');
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');
  const winRateSpan = document.getElementById('winRate');
  const profitLossSpan = document.getElementById('profitLoss');
  const totalTradesSpan = document.getElementById('totalTrades');
  const lastTradeTimeSpan = document.getElementById('lastTradeTime');
  const statusIndicator = document.getElementById('statusIndicator');
  const errorContainer = document.getElementById('errorContainer');
  
  // Spatial analysis elements
  const detectedElementsSpan = document.getElementById('detectedElements');
  const topElementsSpan = document.getElementById('topElements');
  const middleElementsSpan = document.getElementById('middleElements');
  const bottomElementsSpan = document.getElementById('bottomElements');
  const detectedPatternsUl = document.getElementById('detectedPatterns');
  const activeStrategiesDiv = document.getElementById('activeStrategies');

  // Load saved settings from storage
  chrome.storage.sync.get([
    'apiKey',
    'omniparserUrl',
    'currencyPair',
    'pollingInterval',
    'lotSize',
    'buyButtonSelector',
    'sellButtonSelector',
    'chartSelector'
  ], function(items) {
    if (items.apiKey) apiKeyInput.value = items.apiKey;
    if (items.omniparserUrl) omniparserUrlInput.value = items.omniparserUrl;
    if (items.currencyPair) currencyPairSelect.value = items.currencyPair;
    if (items.pollingInterval) pollingIntervalInput.value = items.pollingInterval;
    if (items.lotSize) lotSizeInput.value = items.lotSize;
    if (items.buyButtonSelector) buyButtonSelectorInput.value = items.buyButtonSelector;
    if (items.sellButtonSelector) sellButtonSelectorInput.value = items.sellButtonSelector;
    if (items.chartSelector) chartSelectorInput.value = items.chartSelector;
  });

  // Load agent status and update UI
  chrome.storage.local.get(['agentRunning'], function(data) {
    updateUIState(data.agentRunning || false);
  });

  // Load performance metrics and spatial analysis data
  chrome.storage.local.get(['tradePerformance', 'lastTrade'], function(data) {
    if (data.tradePerformance) {
      updatePerformanceMetrics(data.tradePerformance);
    }
    
    if (data.lastTrade) {
      updateSpatialAnalysis(data.lastTrade);
    }
  });

  // Save settings when inputs change
  function saveSettings() {
    chrome.storage.sync.set({
      apiKey: apiKeyInput.value,
      omniparserUrl: omniparserUrlInput.value,
      currencyPair: currencyPairSelect.value,
      pollingInterval: pollingIntervalInput.value,
      lotSize: lotSizeInput.value,
      buyButtonSelector: buyButtonSelectorInput.value,
      sellButtonSelector: sellButtonSelectorInput.value,
      chartSelector: chartSelectorInput.value
    });
  }

  // Add change listeners to all inputs
  [
    apiKeyInput, omniparserUrlInput, currencyPairSelect, pollingIntervalInput,
    lotSizeInput, buyButtonSelectorInput, sellButtonSelectorInput, chartSelectorInput
  ].forEach(element => {
    element.addEventListener('change', saveSettings);
  });

  // Start agent button
  startBtn.addEventListener('click', function() {
    if (!validateSettings()) return;
    
    saveSettings();
    chrome.runtime.sendMessage({ action: 'startAgent' });
    updateUIState(true);
  });

  // Stop agent button
  stopBtn.addEventListener('click', function() {
    chrome.runtime.sendMessage({ action: 'stopAgent' });
    updateUIState(false);
  });

  // Validate settings before starting
  function validateSettings() {
    if (!apiKeyInput.value) {
      showError('Please enter an OpenAI API key');
      return false;
    }
    if (!omniparserUrlInput.value) {
      showError('Please enter an OmniParser URL');
      return false;
    }
    if (!buyButtonSelectorInput.value || !sellButtonSelectorInput.value || !chartSelectorInput.value) {
      showError('Please enter DOM selectors for the buy/sell buttons and chart');
      return false;
    }
    return true;
  }

  // Update UI state based on agent running status
  function updateUIState(isRunning) {
    if (isRunning) {
      startBtn.disabled = true;
      stopBtn.disabled = false;
    } else {
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  }
  
  // Show error message
  function showError(message) {
    errorContainer.textContent = message;
    errorContainer.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
      errorContainer.style.display = 'none';
    }, 10000);
  }
  
  // Update performance metrics display
  function updatePerformanceMetrics(data) {
    if (data.winRate !== undefined) {
      winRateSpan.textContent = data.winRate.toFixed(1) + '%';
      // Add color coding based on win rate
      if (parseFloat(data.winRate) > 60) {
        winRateSpan.className = 'metric-value success';
      } else if (parseFloat(data.winRate) < 40) {
        winRateSpan.className = 'metric-value danger';
      } else {
        winRateSpan.className = 'metric-value neutral';
      }
    }
    
    if (data.profitLoss !== undefined) {
      profitLossSpan.textContent = '$' + data.profitLoss.toFixed(2);
    }
    
    if (data.totalTrades !== undefined) {
      totalTradesSpan.textContent = data.totalTrades;
    }
    
    // Update status indicator
    if (statusIndicator) {
      let statusClass = 'neutral';
      if (data.winRate > 60) statusClass = 'success';
      else if (data.winRate < 40) statusClass = 'danger';
      
      statusIndicator.className = `status-dot ${statusClass}`;
      statusIndicator.title = `Win Rate: ${data.winRate}%`;
    }
  }
  
  // Update spatial analysis display
  function updateSpatialAnalysis(trade) {
    // Update detected elements count
    if (trade.parsedContentList && detectedElementsSpan) {
      detectedElementsSpan.textContent = trade.parsedContentList.length;
    }
    
    // Update spatial distribution
    if (trade.spatialSummary) {
      if (topElementsSpan) topElementsSpan.textContent = trade.spatialSummary.top || 0;
      if (middleElementsSpan) middleElementsSpan.textContent = trade.spatialSummary.middle || 0;
      if (bottomElementsSpan) bottomElementsSpan.textContent = trade.spatialSummary.bottom || 0;
    }
    
    // Update patterns
    if (trade.marketData && trade.marketData.candlestick_patterns && detectedPatternsUl) {
      detectedPatternsUl.innerHTML = '';
      
      if (trade.marketData.candlestick_patterns.length === 0) {
        detectedPatternsUl.innerHTML = '<li>No patterns detected</li>';
      } else {
        trade.marketData.candlestick_patterns.forEach(pattern => {
          const li = document.createElement('li');
          li.textContent = pattern.replace(/_/g, ' ');
          detectedPatternsUl.appendChild(li);
        });
      }
    }
    
    // Update active strategies
    if (trade.strategies_triggered && activeStrategiesDiv) {
      activeStrategiesDiv.innerHTML = '';
      
      if (!trade.strategies_triggered.length) {
        activeStrategiesDiv.textContent = 'No strategies active';
      } else {
        trade.strategies_triggered.forEach(strategy => {
          const chip = document.createElement('span');
          chip.className = 'status-chip';
          chip.textContent = strategy;
          
          // Add colors based on strategy confidence
          if (trade.confidence > 0.7) {
            chip.classList.add('strong');
          } else if (trade.confidence < 0.4) {
            chip.classList.add('weak');
          } else {
            chip.classList.add('neutral');
          }
          
          activeStrategiesDiv.appendChild(chip);
        });
      }
    }
    
    // Update last trade time
    if (trade.timestamp && lastTradeTimeSpan) {
      const date = new Date(trade.timestamp);
      lastTradeTimeSpan.textContent = date.toLocaleTimeString();
    }
  }

  // Listen for updates from background script
  chrome.runtime.onMessage.addListener(function(message) {
    console.log('Popup received message:', message);
    
    if (message.action === 'updateMetrics') {
      updatePerformanceMetrics(message);
    }
    
    if (message.action === 'statusUpdate') {
      if (statusIndicator) {
        statusIndicator.className = `status-dot ${message.status.type}`;
        statusIndicator.title = message.status.message;
      }
    }
    
    if (message.action === 'tradeLogged') {
      updateSpatialAnalysis(message.trade);
    }
    
    // Handle error messages
    if (message.action === 'error') {
      showError(message.message || 'Unknown error');
    }
  });

  // Add refresh button functionality
  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', function() {
      chrome.runtime.sendMessage({ action: 'getAgentStatus' }, function(response) {
        if (response) {
          updatePerformanceMetrics(response.tradePerformance || {});
          
          // Get the latest trade for spatial analysis
          chrome.storage.local.get('tradeHistory', function(data) {
            if (data.tradeHistory && data.tradeHistory.length > 0) {
              updateSpatialAnalysis(data.tradeHistory[data.tradeHistory.length - 1]);
            }
          });
        }
      });
    });
  }
}); 