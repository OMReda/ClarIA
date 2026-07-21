import { chromium } from 'playwright';
import path from 'path';

(async () => {
  console.log('--- STARTING NETWORK VERIFICATION SCRIPT ---');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const networkLog = [];
  page.on('request', request => {
    if (request.url().includes('/api/v1/files/') && request.url().includes('/data')) {
      const logLine = `[NETWORK] ${new Date().toISOString()} | ${request.method()} ${request.url()}`;
      networkLog.push(logLine);
      console.log(logLine);
    }
  });

  try {
    await page.goto('http://localhost:4173');
    await page.waitForSelector('.upload-zone', { state: 'visible' });

    const filePath = path.resolve('../Fake_SAP_Dataset_5000_Rows.xlsx');
    console.log(`[ACTION] Uploading file: ${filePath}`);
    
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('.upload-zone');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);

    await page.waitForSelector('button[title="Ouvrir dans Dashboard"]', { timeout: 30000 });
    
    console.log('[ACTION] Clicking Dashboard...');
    const dashboardBtn = await page.locator('button[title="Ouvrir dans Dashboard"]');
    await dashboardBtn.click();
    
    console.log('[ACTION] Clicking Ajouter un graphique...');
    await page.locator('button.db-empty__cta').click();
    
    // Wait for the builder to fully mount
    await page.waitForSelector('select#x-col-select', { timeout: 15000 });
    console.log('[ACTION] Dashboard Builder loaded. Waiting 2 seconds to ensure initial data fetch completes...');
    await page.waitForTimeout(2000);

    console.log('[ACTION] Changing X-Axis to index 1...');
    await page.selectOption('select#x-col-select', { index: 1 });
    await page.waitForTimeout(1000);

    console.log('[ACTION] Changing Y-Axis to index 1...');
    await page.selectOption('select#y-col-select', { index: 1 });
    await page.waitForTimeout(1000);

    console.log('[ACTION] Changing Aggregation to count...');
    await page.selectOption('select#agg-select', 'count');
    await page.waitForTimeout(1000);

    console.log('[ACTION] Changing X-Axis to index 2...');
    await page.selectOption('select#x-col-select', { index: 2 });
    await page.waitForTimeout(1000);

    console.log('\n--- NETWORK REQUEST LOG FOR /data ---');
    if (networkLog.length === 0) {
      console.log('No /data requests captured.');
    } else {
      networkLog.forEach(log => console.log(log));
    }
    console.log(`Total /data API calls made: ${networkLog.length}`);
    console.log('--- END OF VERIFICATION ---');

  } catch (error) {
    console.error('Error during verification:', error);
    await page.screenshot({ path: 'verify_network_screenshot.png' });
  } finally {
    await browser.close();
  }
})();
