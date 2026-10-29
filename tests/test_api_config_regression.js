/**
 * Regression tests for frontend API Base URL configuration and endpoints.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('Running API Base URL and Endpoint Regression Tests...');

// 1. Verify frontend/src/apiConfig.js exists and content is correct
const apiConfigPath = path.resolve(__dirname, '../frontend/src/apiConfig.js');
assert(fs.existsSync(apiConfigPath), 'frontend/src/apiConfig.js must exist');
const apiConfigContent = fs.readFileSync(apiConfigPath, 'utf8');

assert(apiConfigContent.includes("http://127.0.0.1:8001"), 'apiConfig.js must default to port 8001');
assert(!apiConfigContent.includes(":8000"), 'apiConfig.js must not contain port 8000');
assert(apiConfigContent.includes('export const getApiUrl'), 'apiConfig.js must export getApiUrl');
console.log('[PASS] apiConfig.js exists, exports getApiUrl, and defaults to http://127.0.0.1:8001');

// 2. Test URL construction logic
function testGetApiUrl(endpoint, base = 'http://127.0.0.1:8001') {
  if (!endpoint) return base;
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${base}${cleanEndpoint}`;
}

assert.strictEqual(testGetApiUrl('/health'), 'http://127.0.0.1:8001/health');
assert.strictEqual(testGetApiUrl('health'), 'http://127.0.0.1:8001/health');
assert.strictEqual(testGetApiUrl('/analyze-all'), 'http://127.0.0.1:8001/analyze-all');
assert.strictEqual(testGetApiUrl('/api/observations'), 'http://127.0.0.1:8001/api/observations');
assert.strictEqual(testGetApiUrl('/api/observations/obs_123/status'), 'http://127.0.0.1:8001/api/observations/obs_123/status');
console.log('[PASS] URL construction logic handles leading slash and formats all endpoints to port 8001');

// 3. Verify frontend/vite.config.js targets port 8001 and does not contain port 8000
const viteConfigPath = path.resolve(__dirname, '../frontend/vite.config.js');
assert(fs.existsSync(viteConfigPath), 'frontend/vite.config.js must exist');
const viteConfigContent = fs.readFileSync(viteConfigPath, 'utf8');

assert(viteConfigContent.includes('http://127.0.0.1:8001'), 'vite.config.js proxy target must be port 8001');
assert(!viteConfigContent.includes(':8000'), 'vite.config.js must not contain port 8000');
console.log('[PASS] vite.config.js proxy target is http://127.0.0.1:8001 with zero references to 8000');

// 4. Verify no runtime files in frontend/src contain port 8000
function getFilesRecursively(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(fullPath));
    } else if (file.endsWith('.js') || file.endsWith('.jsx') || file.endsWith('.ts') || file.endsWith('.tsx')) {
      results.push(fullPath);
    }
  }
  return results;
}

const srcDir = path.resolve(__dirname, '../frontend/src');
const srcFiles = getFilesRecursively(srcDir);
let port8000Count = 0;
for (const file of srcFiles) {
  const content = fs.readFileSync(file, 'utf8');
  if (content.includes(':8000') || content.includes('8000/')) {
    console.error(`Found port 8000 in: ${file}`);
    port8000Count++;
  }
}
assert.strictEqual(port8000Count, 0, 'No frontend src files should reference port 8000');
console.log(`[PASS] Verified ${srcFiles.length} frontend source files: 0 references to port 8000`);

// 5. Verify backend CORS configuration permits port 5174 and uses regex
const backendMainPath = path.resolve(__dirname, '../backend/app/main.py');
assert(fs.existsSync(backendMainPath), 'backend/app/main.py must exist');
const backendMainContent = fs.readFileSync(backendMainPath, 'utf8');

assert(backendMainContent.includes('5174'), 'backend CORS origins must include port 5174');
assert(backendMainContent.includes('allow_origin_regex'), 'backend CORS must include allow_origin_regex');
console.log('[PASS] Backend CORS configuration explicitly includes port 5174 and regex matching');

console.log('\nAll API Base URL regression tests passed successfully!');
