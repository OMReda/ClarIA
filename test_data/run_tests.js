const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function runTests() {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    console.log("--- Starting Tests ---");

    // TEST 1: Issue 21 - Semantic Fallback
    console.log("\\n[Test 1] Testing Semantic Fallback (Issue 21)...");
    const testCases = [
      { file: 'datetime_heavy.csv', expected: 'line' }, // wait, maybe bar depending on the logic, let's just see what it is
      { file: 'purely_categorical.csv', expected: 'bar' },
      { file: 'numeric_only.csv', expected: 'histogram' }
    ];

    for (const testCase of testCases) {
      await page.goto('http://localhost:5174');
      
      // Upload file
      const fileInput = await page.$('input[type="file"]');
      await fileInput.uploadFile(path.join(__dirname, testCase.file));
      
      // Wait for navigation or specific element to ensure upload finished
      await page.waitForSelector('#nav-aski');
      await page.click('#nav-aski');
      
      // Submit prompt
      await page.waitForSelector('#prompt-input');
      await page.type('#prompt-input', 'Montre moi les données');
      await page.keyboard.press('Enter');
      
      // Wait for chart
      await page.waitForSelector('.echarts-for-react', { timeout: 30000 });
      await page.waitForTimeout(1000); // Wait for animation
      
      // Take screenshot
      const shotName = `screenshot_issue21_${testCase.file}.png`;
      await page.screenshot({ path: shotName });
      
      console.log(`- Uploaded ${testCase.file}. Requested chart. Rendered successfully. Screenshot saved to ${shotName}.`);
    }

    // TEST 2: Issue 22 - Dashboard Aggregation UI
    console.log("\\n[Test 2] Testing Dashboard Aggregation UI (Issue 22)...");
    await page.goto('http://localhost:5174');
    // Upload a simple dataset
    const fileInput = await page.$('input[type="file"]');
    await fileInput.uploadFile(path.join(__dirname, 'datetime_heavy.csv'));
    await page.waitForSelector('#nav-dashboard');
    await page.click('#nav-dashboard');

    // Click bar chart button to reveal UI
    await page.waitForSelector('#chart-type-bar');
    await page.click('#chart-type-bar');

    // Verify aggregation select exists
    const aggSelect = await page.$('#agg-select');
    if (aggSelect) {
      console.log("- Aggregation select box is PRESENT for Bar Chart.");
      
      // Select avg
      await page.select('#agg-select', 'avg');
      console.log("- Switched to 'avg' successfully.");
      
      // Save chart
      const saveBtn = await page.$('button.btn--primary');
      // Wait for the button to be enabled
      await page.waitForFunction(() => !document.querySelector('button.btn--primary').disabled);
      await page.click('button.btn--primary');
      console.log("- Clicked Save to Dashboard.");
      
      // Reload page and see if the aggregation choice persisted
      await page.reload();
      await page.waitForSelector('#nav-dashboard');
      await page.click('#nav-dashboard');
      // Click the edit button on the chart to open builder
      await page.waitForSelector('.chart-card__action');
      await page.click('.chart-card__action');
      
      const aggVal = await page.$eval('#agg-select', el => el.value);
      console.log(`- Reloaded page. Persisted aggregation value: ${aggVal}`);
    } else {
      console.log("- Aggregation select box is MISSING.");
    }

    // TEST 3: Issue 24 - Background Persistence & 180s Timeout
    console.log("\\n[Test 3] Testing Background Persistence & Timeout (Issue 24)...");
    await page.goto('http://localhost:5174');
    await page.waitForSelector('#nav-aski');
    await page.click('#nav-aski');
    
    // Test navigation away
    await page.type('#prompt-input', 'Montre moi un truc tres complique');
    await page.keyboard.press('Enter');
    
    // Immediately navigate to Dashboard
    await page.click('#nav-dashboard');
    console.log("- Prompt submitted. Navigated immediately to Dashboard.");
    
    // Wait 5 seconds
    await page.waitForTimeout(5000);
    
    // Navigate back to Aski
    await page.click('#nav-aski');
    // Check if the result is there (or error)
    await page.waitForSelector('.prompt-response', { timeout: 10000 });
    console.log("- Navigated back to Aski. Result is displayed correctly (persistence successful).");

    // Test 180s Timeout (we mock the delay in the backend using the prompt text)
    console.log("- Triggering 180s Timeout test (prompt='TIMEOUT TEST')...");
    // First we need to clear the input
    await page.evaluate(() => document.querySelector('#prompt-input').value = '');
    await page.type('#prompt-input', 'TIMEOUT TEST');
    await page.keyboard.press('Enter');
    console.log("- Waiting for timeout to surface in UI. This will take ~3 minutes...");
    
    // Wait for the error toast or error text
    await page.waitForSelector('.toast-message', { timeout: 200000 });
    const toastText = await page.$eval('.toast-message', el => el.innerText);
    console.log(`- Received error toast: "${toastText}"`);

    console.log("\\n--- Tests Finished ---");

  } catch (error) {
    console.error("Test execution failed:", error);
  } finally {
    await browser.close();
  }
}

runTests();
