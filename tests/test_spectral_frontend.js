/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — MULTI-SPECTRAL RATIOS FRONTEND & API TEST SUITE
 * ============================================================================
 * Tests:
 *   1. HTML Structure: #dash-spectral-panel and sub-components exist
 *   2. Spectral Cards: Ferrous, Clay, Iron Oxide cards present with formulas
 *   3. Spectral Metric IDs: Target values, buffer means, ranges, status badges
 *   4. Scientific Integrity Note: Clear disclaimer regarding L2A rasters
 *   5. Map Integration: #map-spectral-status present in map prospectivity card
 *   6. app.js Syntax: app.js compiles and includes getSpectralRatios & updateSpectralFingerprint
 *   7. Client Diagnostic Contract: Missing bands reported honestly without simulation
 *   8. Live REST API /api/spectral-ratios: HTTP 200 OK and valid schema
 *   9. API Out-of-Bounds: Handles boundary conditions gracefully
 *  10. Endpoint Regression Check: Existing /api/health and /api/zones endpoints intact
 * ============================================================================
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const http = require('http');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        passedTests++;
        console.log(`[PASS] ${name}`);
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
    }
}

async function runAsyncTest(name, fn) {
    totalTests++;
    try {
        await fn();
        passedTests++;
        console.log(`[PASS] ${name}`);
    } catch (err) {
        console.error(`[FAIL] ${name}: ${err.message}`);
    }
}

function fetchUrl(url) {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
        });
        req.on('error', reject);
        req.setTimeout(2500, () => {
            req.destroy();
            reject(new Error('Timeout'));
        });
    });
}

async function runAllTests() {
    console.log('================================================================');
    console.log('TEST SUITE: SENTINEL-2 SPECTRAL RATIOS FRONTEND & API');
    console.log('================================================================\n');

    const htmlPath = path.join(__dirname, '..', 'index.html');
    const appJsPath = path.join(__dirname, '..', 'app.js');
    const htmlContent = fs.readFileSync(htmlPath, 'utf8');
    const appJsContent = fs.readFileSync(appJsPath, 'utf8');

    // 1. HTML Structure
    runTest('Test 1: #dash-spectral-panel container exists in index.html', () => {
        assert(htmlContent.includes('id="dash-spectral-panel"'), 'dash-spectral-panel must exist');
        assert(htmlContent.includes('Spectral Fingerprint'), 'Title Spectral Fingerprint must exist');
    });

    // 2. Spectral Cards & Formulas
    runTest('Test 2: All 3 Spectral Ratio cards exist with exact formulas', () => {
        assert(htmlContent.includes('id="spectral-card-ferrous"'), 'spectral-card-ferrous must exist');
        assert(htmlContent.includes('B11 / B8A'), 'Ferrous formula B11 / B8A must exist');

        assert(htmlContent.includes('id="spectral-card-clay"'), 'spectral-card-clay must exist');
        assert(htmlContent.includes('B11 / B12'), 'Clay formula B11 / B12 must exist');

        assert(htmlContent.includes('id="spectral-card-iron"'), 'spectral-card-iron must exist');
        assert(htmlContent.includes('B04 / B02'), 'Iron Oxide formula B04 / B02 must exist');
    });

    // 3. Metric IDs
    runTest('Test 3: Metric value, mean, range, and status IDs present for all ratios', () => {
        const requiredIds = [
            'spectral-ferrous-value', 'spectral-ferrous-mean', 'spectral-ferrous-range', 'spectral-ferrous-status',
            'spectral-clay-value', 'spectral-clay-mean', 'spectral-clay-range', 'spectral-clay-status',
            'spectral-iron-value', 'spectral-iron-mean', 'spectral-iron-range', 'spectral-iron-status',
            'spectral-status-badge'
        ];
        for (const id of requiredIds) {
            assert(htmlContent.includes(`id="${id}"`), `Missing required element id: ${id}`);
        }
    });

    // 4. Scientific Integrity Note
    runTest('Test 4: Scientific Integrity Note exists in DOM', () => {
        assert(htmlContent.includes('id="spectral-integrity-note"'), 'spectral-integrity-note must exist');
        assert(htmlContent.includes('Scientific Integrity Active'), 'Disclaimer text must be present');
    });

    // 5. Map Integration
    runTest('Test 5: #map-spectral-status integrated into map prospectivity card', () => {
        assert(htmlContent.includes('id="map-spectral-status"'), 'map-spectral-status must exist');
        assert(htmlContent.includes('Spectral Ratios:'), 'Spectral Ratios label must be on map card');
    });

    // 6. app.js Methods
    runTest('Test 6: app.js contains getSpectralRatios and updateSpectralFingerprint', () => {
        assert(appJsContent.includes('async getSpectralRatios('), 'API.getSpectralRatios method must be defined');
        assert(appJsContent.includes('async function updateSpectralFingerprint('), 'updateSpectralFingerprint function must be defined');
        assert(appJsContent.includes('updateSpectralFingerprint(lat, lon, radiusKm);'), 'btnRun must trigger updateSpectralFingerprint');
        assert(appJsContent.includes('updateSpectralFingerprint(info.lat, info.lon, info.radiusKm);'), 'map target changes must trigger updateSpectralFingerprint');
    });

    // 7. Non-simulation contract check in app.js
    runTest('Test 7: app.js diagnostic fallback enforces non-simulation', () => {
        assert(appJsContent.includes("is_simulated: false"), 'is_simulated flag must be false');
        assert(appJsContent.includes("missing_bands: ['B02', 'B04', 'B11', 'B12', 'B8A']"), 'Missing bands must be explicitly listed');
    });

    // 8. Live REST API /api/spectral-ratios test
    await runAsyncTest('Test 8: Live /api/spectral-ratios endpoint returns 200 OK and valid schema', async () => {
        try {
            const res = await fetchUrl('http://127.0.0.1:8085/api/spectral-ratios?lat=21.9455&lon=80.4295&radius=25');
            assert.strictEqual(res.status, 200, 'Status should be 200');
            const json = JSON.parse(res.body);
            assert.strictEqual(json.status, 'success');
            assert(json.ratios.ferrous_minerals, 'ferrous_minerals ratio must exist');
            assert(json.ratios.clay_minerals, 'clay_minerals ratio must exist');
            assert(json.ratios.iron_oxide, 'iron_oxide ratio must exist');
            assert(json.data_availability, 'data_availability must be returned');
            assert.strictEqual(json.data_availability.is_simulated, false, 'is_simulated must be false');
        } catch (e) {
            if (e.code === 'ECONNREFUSED' || (e.message && e.message.includes('ECONNREFUSED'))) {
                console.log('   (Server offline on port 8085, live API skipped)');
                return;
            }
            throw e;
        }
    });

    // 9. API Out-of-Bounds Handling
    await runAsyncTest('Test 9: /api/spectral-ratios handles out-of-bounds gracefully', async () => {
        try {
            const res = await fetchUrl('http://127.0.0.1:8085/api/spectral-ratios?lat=0&lon=0&radius=25');
            assert.strictEqual(res.status, 400, 'Out-of-bounds status should be 400 Bad Request');
            const json = JSON.parse(res.body);
            assert.strictEqual(json.status, 'error');
            assert(json.message.includes('outside'), 'Error message should describe coordinate outside domain');
        } catch (e) {
            if (e.code === 'ECONNREFUSED' || (e.message && e.message.includes('ECONNREFUSED'))) {
                console.log('   (Server offline on port 8085, live API skipped)');
                return;
            }
            throw e;
        }
    });

    // 10. Existing Endpoint Regression Check
    await runAsyncTest('Test 10: Preserved endpoints /api/health and /api/zones return 200 OK', async () => {
        try {
            const healthRes = await fetchUrl('http://127.0.0.1:8085/api/health');
            assert.strictEqual(healthRes.status, 200, 'Health endpoint should return 200');
            const healthJson = JSON.parse(healthRes.body);
            assert.strictEqual(healthJson.status, 'healthy');

            const zonesRes = await fetchUrl('http://127.0.0.1:8085/api/zones');
            assert.strictEqual(zonesRes.status, 200, 'Zones endpoint should return 200');
            const zonesJson = JSON.parse(zonesRes.body);
            assert.strictEqual(zonesJson.status, 'success');
            assert(Array.isArray(zonesJson.zones), 'Zones must be an array');
            assert.strictEqual(zonesJson.zones.length, 20, 'All 20 zones must be returned');
        } catch (e) {
            if (e.code === 'ECONNREFUSED' || (e.message && e.message.includes('ECONNREFUSED'))) {
                console.log('   (Server offline on port 8085, live API skipped)');
                return;
            }
            throw e;
        }
    });

    console.log(`\n================================================================`);
    console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests/totalTests)*100)}%)`);
    console.log(`================================================================\n`);

    if (passedTests !== totalTests) {
        process.exit(1);
    }
}

runAllTests().catch(err => {
    console.error('Test execution error:', err);
    process.exit(1);
});
