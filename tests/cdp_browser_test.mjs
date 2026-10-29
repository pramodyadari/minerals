// Comprehensive CDP-based real Chrome browser verification
// Tests 3D terrain rendering, WebGL context loss prevention, and 2/3 custom mineral selection
import { spawn } from 'child_process';
import http from 'http';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const PORT = 9222;

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function getWsUrl() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await new Promise((resolve, reject) => {
        http.get(`http://127.0.0.1:${PORT}/json/version`, (resp) => {
          let data = '';
          resp.on('data', (c) => (data += c));
          resp.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
      });
      if (res && res.webSocketDebuggerUrl) {
        return res.webSocketDebuggerUrl;
      }
    } catch (e) {
      await wait(300);
    }
  }
  throw new Error('Chrome did not start or debugging port not available');
}

async function run() {
  console.log('--- STARTING REAL CHROME END-TO-END VERIFICATION ---');
  const chromeProc = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    '--enable-webgl',
    '--ignore-gpu-blocklist',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-default-apps',
    '--disable-extensions',
    '--no-sandbox',
    '--user-data-dir=C:\\Users\\yadar\\AppData\\Local\\Temp\\chrome-e2e-profile',
    'about:blank'
  ]);

  const consoleLogs = [];
  const consoleErrors = [];

  try {
    const wsUrl = await getWsUrl();
    const ws = new WebSocket(wsUrl);
    let msgId = 1;
    const callbacks = new Map();

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.id && callbacks.has(data.id)) {
        callbacks.get(data.id)(data);
        callbacks.delete(data.id);
      }
      if (data.method === 'Runtime.consoleAPICalled') {
        const text = data.params.args.map((a) => a.value || JSON.stringify(a)).join(' ');
        consoleLogs.push({ type: data.params.type, text });
        if (data.params.type === 'error' || text.includes('WebGL context lost') || text.includes('Worker failed')) {
          consoleErrors.push(text);
          console.error(`[BROWSER ERROR/WARNING]: ${text}`);
        }
      }
    };

    await new Promise((resolve) => (ws.onopen = resolve));

    function send(method, params = {}) {
      const id = msgId++;
      return new Promise((resolve) => {
        callbacks.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    const target = await send('Target.createTarget', { url: 'http://localhost:5173/' });
    const targetId = target.result.targetId;
    const session = await send('Target.attachToTarget', { targetId, flatten: true });
    const sessionId = session.result.sessionId;

    function evalSession(expr) {
      const id = msgId++;
      return new Promise((resolve) => {
        callbacks.set(id, (res) => resolve(res.result?.result?.value));
        ws.send(JSON.stringify({ id, sessionId, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true } }));
      });
    }

    await evalSession('1+1');
    console.log('1. Navigating to application at http://localhost:5173/ ...');
    await wait(3000);

    // Initial State Check
    const state1 = await evalSession(`(() => {
      return {
        title: document.title,
        hasMapCanvas: !!document.getElementById('exploration-map'),
        has3DContainer: !!document.getElementById('terrain-map-container'),
        modeBtnAllFour: !!document.getElementById('btn-mode-analyze-all-four'),
        modeBtnChoose: !!document.getElementById('btn-mode-choose-minerals'),
        primaryBtnText: document.getElementById('btn-analyze-all-minerals')?.innerText?.trim(),
      };
    })()`);
    console.log('Initial UI state:', state1);

    // 2. Click 3D Terrain button
    console.log('2. Switching to 3D Terrain view...');
    await evalSession(`document.getElementById('btn-switch-3d-terrain')?.click()`);
    await wait(3000);

    const terrainState = await evalSession(`(() => {
      const canvas = document.querySelector('.maplibregl-canvas');
      const errorView = document.getElementById('terrain-render-error-view');
      return {
        has3DContainer: !!document.getElementById('terrain-map-container'),
        hasCanvas: !!canvas,
        canvasWidth: canvas?.width || 0,
        canvasHeight: canvas?.height || 0,
        hasErrorView: !!errorView,
        errorText: errorView?.innerText || null,
      };
    })()`);
    console.log('3D Terrain state:', terrainState);

    // 3. Test Mode Toggle: Switch to "Choose Minerals"
    console.log('3. Switching to "Choose Minerals" mode...');
    await evalSession(`document.getElementById('btn-mode-choose-minerals')?.click()`);
    await wait(1000);

    const customModeState1 = await evalSession(`(() => {
      return {
        hasControlsPanel: !!document.getElementById('custom-mode-controls-panel'),
        primaryBtnText: document.getElementById('btn-analyze-all-minerals')?.innerText?.trim(),
        badgeText: document.getElementById('mineral-selection-badge')?.innerText?.trim(),
      };
    })()`);
    console.log('Choose Minerals mode active:', customModeState1);

    // 4. Test selecting a 3rd mineral: Click "Iron Ore" card
    console.log('4. Selecting a 3rd mineral (Iron Ore)...');
    await evalSession(`(() => {
      const card = document.getElementById('mineral-card-iron-ore');
      if (card) card.click();
    })()`);
    await wait(1000);

    const customModeState2 = await evalSession(`(() => {
      return {
        primaryBtnText: document.getElementById('btn-analyze-all-minerals')?.innerText?.trim(),
        badgeText: document.getElementById('mineral-selection-badge')?.innerText?.trim(),
      };
    })()`);
    console.log('State with 3 minerals selected:', customModeState2);

    // 5. Click "Select All Four" shortcut
    console.log('5. Clicking "Select All Four" shortcut...');
    await evalSession(`document.getElementById('btn-select-all-four-shortcut')?.click()`);
    await wait(1000);

    const allFourState = await evalSession(`(() => {
      return {
        primaryBtnText: document.getElementById('btn-analyze-all-minerals')?.innerText?.trim(),
        badgeText: document.getElementById('mineral-selection-badge')?.innerText?.trim(),
      };
    })()`);
    console.log('State after clicking Select All Four:', allFourState);

    // 6. Final verification of console errors and 3D canvas
    const finalCanvasCheck = await evalSession(`(() => {
      const canvas = document.querySelector('.maplibregl-canvas');
      return {
        canvasActive: !!canvas,
        width: canvas?.width || 0,
        height: canvas?.height || 0,
        renderError: !!document.getElementById('terrain-render-error-view'),
      };
    })()`);
    console.log('Final 3D Canvas check:', finalCanvasCheck);

    console.log('Total console error count:', consoleErrors.length);

    ws.close();

    // Assertions
    if (!terrainState.hasCanvas || terrainState.hasErrorView) {
      throw new Error(`3D Terrain failed to render: ${terrainState.errorText}`);
    }
    if (consoleErrors.length > 0) {
      throw new Error(`Browser console recorded errors: ${JSON.stringify(consoleErrors)}`);
    }
    if (!customModeState1.primaryBtnText.toLowerCase().includes('analyze selected 2 minerals')) {
      throw new Error(`Expected button text "Analyze Selected 2 Minerals", got: "${customModeState1.primaryBtnText}"`);
    }
    if (!customModeState2.primaryBtnText.toLowerCase().includes('analyze selected 3 minerals')) {
      throw new Error(`Expected button text "Analyze Selected 3 Minerals", got: "${customModeState2.primaryBtnText}"`);
    }
    if (!allFourState.primaryBtnText.toLowerCase().includes('analyze all four minerals')) {
      throw new Error(`Expected button text "Analyze All Four Minerals", got: "${allFourState.primaryBtnText}"`);
    }

    console.log('\n================================================================');
    console.log('REAL BROWSER VERIFICATION: ALL CHECKS PASSED PERFECTLY!');
    console.log('================================================================');
  } catch (err) {
    console.error('Real browser verification failed:', err);
    process.exit(1);
  } finally {
    chromeProc.kill();
  }
}

run();
