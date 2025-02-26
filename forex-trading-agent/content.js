// Content script that runs on Exness trading pages
console.log('Forex Trading Agent: content script loaded');

// Initialize message listener
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log('Content script received message:', request);
  
  switch(request.action) {
    case 'captureScreenshot':
      captureScreenshot(request.chartSelector)
        .then(base64Image => {
          sendResponse({ success: true, image: base64Image });
        })
        .catch(error => {
          console.error('Screenshot capture error:', error);
          sendResponse({ success: false, error: error.message });
        });
      return true; // Keep the message channel open for async response
      
    case 'executeTrade':
      executeTrade(request.direction, request.selectors, request.lotSize)
        .then(result => {
          sendResponse({ success: true, result });
        })
        .catch(error => {
          console.error('Trade execution error:', error);
          sendResponse({ success: false, error: error.message });
        });
      return true; // Keep the message channel open for async response
      
    case 'checkStatus':
      sendResponse({ success: true, status: 'active' });
      return false;
  }
});

/**
 * Captures a screenshot of the chart area
 * @param {string} chartSelector - CSS selector for the chart element
 * @returns {Promise<string>} - Base64-encoded image
 */
async function captureScreenshot(chartSelector) {
  // Dynamically load html2canvas if not already loaded
  if (typeof html2canvas === 'undefined') {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://html2canvas.hertzen.com/dist/html2canvas.min.js';
      script.onload = () => {
        captureWithHtml2Canvas(chartSelector).then(resolve).catch(reject);
      };
      script.onerror = () => {
        reject(new Error('Failed to load html2canvas'));
      };
      document.head.appendChild(script);
    });
  } else {
    return captureWithHtml2Canvas(chartSelector);
  }
}

/**
 * Uses html2canvas to capture a screenshot
 * @param {string} chartSelector - CSS selector for the chart element
 * @returns {Promise<string>} - Base64-encoded image
 */
async function captureWithHtml2Canvas(chartSelector) {
  const chartElement = document.querySelector(chartSelector);
  
  if (!chartElement) {
    throw new Error(`Chart element not found with selector: ${chartSelector}`);
  }
  
  try {
    const canvas = await html2canvas(chartElement, {
      logging: false,
      useCORS: true,
      allowTaint: true
    });
    
    return canvas.toDataURL('image/png');
  } catch (error) {
    console.error('html2canvas error:', error);
    throw new Error('Failed to capture screenshot: ' + error.message);
  }
}

/**
 * Helper function to safely find elements and provide descriptive errors
 * @param {string} selector - CSS selector
 * @param {string} elementName - Human-readable element name for error messages
 * @returns {HTMLElement} - The found element
 * @throws {Error} If element not found
 */
function queryElement(selector, elementName) {
  const element = document.querySelector(selector);
  if (!element) {
    throw new Error(`${elementName} not found with selector: ${selector}`);
  }
  return element;
}

/**
 * Executes a trade by clicking the appropriate button
 * @param {string} direction - 'buy' or 'sell'
 * @param {Object} selectors - Object containing DOM selectors
 * @param {number} lotSize - Size of the trade
 * @returns {Promise<Object>} - Result of the trade
 */
async function executeTrade(direction, selectors, lotSize) {
  try {
    // Validate direction
    if (direction !== 'buy' && direction !== 'sell') {
      throw new Error(`Invalid trade direction: ${direction}`);
    }
    
    // Validate inputs
    if (!selectors) {
      throw new Error('No selectors provided for DOM elements');
    }
    
    // Get the appropriate button based on direction
    const buttonSelector = direction === 'buy' ? 
      (selectors.buyButtonSelector || '#buy-btn') : 
      (selectors.sellButtonSelector || '#sell-btn');
    
    // Set lot size if the platform has a lot size input
    if (selectors.lotSizeInputSelector) {
      try {
        const lotSizeInput = queryElement(selectors.lotSizeInputSelector, "Quantity Input");
        
        // Clear existing value
        lotSizeInput.value = '';
        
        // Set new value (default to 0.01 if not provided)
        lotSizeInput.value = (lotSize || 0.01).toString();
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        lotSizeInput.dispatchEvent(event);
        
        // Also try to trigger input event
        const inputEvent = new Event('input', { bubbles: true });
        lotSizeInput.dispatchEvent(inputEvent);
        
        // Wait for the value to be applied
        await new Promise(resolve => setTimeout(resolve, 500));
        
        console.log(`Set lot size to ${lotSize || 0.01}`);
      } catch (error) {
        console.warn(`Warning: Failed to set lot size: ${error.message}`);
        // Continue with the trade even if setting lot size fails
      }
    }
    
    // Click the button to execute the trade
    const button = queryElement(buttonSelector, `${direction.toUpperCase()} Button`);
    
    // Optional: scroll the button into view
    button.scrollIntoView({ behavior: "smooth", block: "center" });
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Click the button
    button.click();
    console.log(`Clicked ${direction} button`);
    
    // Return details about the executed trade
    return {
      success: true,
      direction,
      timestamp: new Date().toISOString(),
      lotSize: lotSize || 0.01,
      profitLoss: "Pending" // To be updated later
    };
  } catch (error) {
    console.error(`Trade execution error: ${error.message}`);
    // Notify the background script of the error
    chrome.runtime.sendMessage({
      action: 'tradeExecutionError',
      error: error.message
    });
    return { 
      success: false, 
      error: error.message,
      timestamp: new Date().toISOString() 
    };
  }
} 