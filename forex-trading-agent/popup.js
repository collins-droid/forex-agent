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

  // Load performance metrics
  chrome.storage.local.get(['winRate', 'profitLoss', 'totalTrades'], function(data) {
    if (data.winRate !== undefined) winRateSpan.textContent = data.winRate + '%';
    if (data.profitLoss !== undefined) profitLossSpan.textContent = '$' + data.profitLoss.toFixed(2);
    if (data.totalTrades !== undefined) totalTradesSpan.textContent = data.totalTrades;
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
      alert('Please enter an OpenAI API key');
      return false;
    }
    if (!omniparserUrlInput.value) {
      alert('Please enter an OmniParser URL');
      return false;
    }
    if (!buyButtonSelectorInput.value || !sellButtonSelectorInput.value || !chartSelectorInput.value) {
      alert('Please enter DOM selectors for the buy/sell buttons and chart');
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

  // Listen for updates from background script
  chrome.runtime.onMessage.addListener(function(message) {
    if (message.action === 'updateMetrics') {
      winRateSpan.textContent = message.winRate + '%';
      profitLossSpan.textContent = '$' + message.profitLoss.toFixed(2);
      totalTradesSpan.textContent = message.totalTrades;
    }
  });
}); 