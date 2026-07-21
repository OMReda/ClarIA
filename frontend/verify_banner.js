import { chromium } from 'playwright';
import path from 'path';

(async () => {
  console.log('Launching browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    console.log('Navigating to app...');
    await page.goto('http://localhost:5173');

    // Wait for the upload page to load
    await page.waitForSelector('.upload-zone', { state: 'visible' });
    console.log('Upload page loaded.');

    const filePath = path.resolve('../Fake_SAP_Dataset_15000_Rows.xlsx');
    console.log(`Uploading file: ${filePath}`);
    
    // Playwright file upload using the file input
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.click('.upload-zone');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(filePath);

    // Wait for upload to complete and page transition
    // It should navigate to /dashboard or we can click Dashboard
    console.log('Waiting for processing...');
    
    // The button might become "Aller au Dashboard" or it automatically switches
    await page.waitForSelector('button[title="Ouvrir dans Dashboard"]', { timeout: 30000 });
    
    // Click the Dashboard button
    console.log('Clicking Dashboard...');
    const dashboardBtn = await page.locator('button[title="Ouvrir dans Dashboard"]');
    await dashboardBtn.click();
    
    // Wait for the manual builder mode. If it asks to view or add, click "Nouveau graphique"
    console.log('Looking for Nouveau graphique or the banner directly...');
    const newGraphBtn = await page.getByText('Nouveau graphique');
    if (await newGraphBtn.isVisible()) {
      await newGraphBtn.click();
    }
    
    // Look for the warning banner text
    console.log('Checking for warning banner...');
    const bannerText = "Fichier très volumineux. Pour préserver les performances du navigateur, le constructeur manuel analyse un échantillon des 10 000 premières lignes";
    await page.waitForSelector(`text=${bannerText}`, { timeout: 10000 });
    console.log('SUCCESS: Truncation banner is visible on screen.');

    // We can also verify that there is exactly 1 network call to /data when changing dropdowns
    console.log('Testing /data network call caching...');
    let dataCallCount = 0;
    page.on('request', request => {
      if (request.url().includes('/data') && request.method() === 'GET') {
        dataCallCount++;
        console.log(`Intercepted /data call #${dataCallCount}`);
      }
    });

    // Change some dropdowns
    console.log('Changing X-Axis...');
    await page.selectOption('select#x-col-select', 'Category');
    await page.waitForTimeout(500);

    console.log('Changing Y-Axis...');
    await page.selectOption('select#y-col-select', 'Amount');
    await page.waitForTimeout(500);
    await page.waitForTimeout(500);

    console.log(`Total /data API calls made: ${dataCallCount}`);
    if (dataCallCount === 0) {
      console.log('The /data endpoint was called 0 times during dropdown changes! (Cached from earlier load)');
    } else {
      console.log(`The /data endpoint was called ${dataCallCount} times during dropdown changes.`);
    }

  } catch (error) {
    console.error('Error during verification:', error);
  } finally {
    await browser.close();
  }
})();
