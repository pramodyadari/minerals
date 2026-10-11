/**
 * ============================================================================
 * MULTI-MINERAL ROUTING SMOKE TEST
 * ============================================================================
 * 
 * Validates that:
 *   1. MineralRegistry is properly defined with all 7 minerals.
 *   2. Manganese is the ONLY trained mineral.
 *   3. All other minerals are framework_ready with no data paths.
 *   4. Registry API functions return correct results.
 *   5. No cross-mineral data leakage is possible.
 * ============================================================================
 */

const assert = require('assert');
const MineralRegistry = require('../js/mineral-registry');

let passed = 0;
let total = 0;

function test(name, fn) {
    total++;
    try {
        fn();
        passed++;
        console.log(`[PASS] ${name}`);
    } catch (e) {
        console.log(`[FAIL] ${name}: ${e.message}`);
    }
}

console.log('================================================================');
console.log('MULTI-MINERAL ROUTING SMOKE TEST');
console.log('================================================================\n');

// --- Test 1: All 7 minerals registered ---
test('All 7 minerals are registered', () => {
    const all = MineralRegistry.getAllMinerals();
    assert.strictEqual(all.length, 7, `Expected 7 minerals, got ${all.length}`);
});

// --- Test 2: Correct mineral IDs ---
test('Correct mineral IDs exist', () => {
    const expectedIds = ['manganese', 'coal', 'bauxite', 'limestone', 'iron_ore', 'copper', 'lithium'];
    expectedIds.forEach(id => {
        const m = MineralRegistry.getMineral(id);
        assert.ok(m, `Mineral '${id}' not found in registry`);
        assert.strictEqual(m.id, id);
    });
});

// --- Test 3: Manganese is trained ---
test('Manganese: status = trained', () => {
    assert.strictEqual(MineralRegistry.isTrained('manganese'), true);
    assert.strictEqual(MineralRegistry.canAnalyze('manganese'), true);
    assert.strictEqual(MineralRegistry.hasZones('manganese'), true);
    assert.strictEqual(MineralRegistry.hasXAI('manganese'), true);
    assert.strictEqual(MineralRegistry.hasProductionModel('manganese'), true);
});

// --- Test 4: Manganese has real data paths ---
test('Manganese: has real model and data paths', () => {
    const mn = MineralRegistry.getMineral('manganese');
    assert.ok(mn.modelPath, 'Manganese must have modelPath');
    assert.ok(mn.gridPath, 'Manganese must have gridPath');
    assert.ok(mn.zonesPath, 'Manganese must have zonesPath');
    assert.ok(mn.rasterPath, 'Manganese must have rasterPath');
    assert.ok(mn.productionModelPath, 'Manganese must have productionModelPath');
    assert.ok(mn.productionTreesPath, 'Manganese must have productionTreesPath');
});

// --- Tests 5-10: Each untrained mineral ---
const untrainedMinerals = ['coal', 'bauxite', 'limestone', 'iron_ore', 'copper', 'lithium'];

untrainedMinerals.forEach(mineralId => {
    const config = MineralRegistry.getMineral(mineralId);

    test(`${config.displayName}: status = framework_ready, NOT trained`, () => {
        assert.strictEqual(config.status, 'framework_ready');
        assert.strictEqual(MineralRegistry.isTrained(mineralId), false);
    });

    test(`${config.displayName}: no model/data available`, () => {
        assert.strictEqual(config.modelAvailable, false);
        assert.strictEqual(config.prospectivityAvailable, false);
        assert.strictEqual(config.zonesAvailable, false);
        assert.strictEqual(config.xaiAvailable, false);
        assert.strictEqual(config.productionModelAvailable, false);
    });

    test(`${config.displayName}: all data paths are null`, () => {
        assert.strictEqual(config.modelPath, null, `${mineralId} modelPath should be null`);
        assert.strictEqual(config.gridPath, null, `${mineralId} gridPath should be null`);
        assert.strictEqual(config.zonesPath, null, `${mineralId} zonesPath should be null`);
        assert.strictEqual(config.rasterPath, null, `${mineralId} rasterPath should be null`);
        assert.strictEqual(config.productionModelPath, null, `${mineralId} productionModelPath should be null`);
        assert.strictEqual(config.productionTreesPath, null, `${mineralId} productionTreesPath should be null`);
    });

    test(`${config.displayName}: canAnalyze/hasZones/hasXAI/hasProductionModel all false`, () => {
        assert.strictEqual(MineralRegistry.canAnalyze(mineralId), false);
        assert.strictEqual(MineralRegistry.hasZones(mineralId), false);
        assert.strictEqual(MineralRegistry.hasXAI(mineralId), false);
        assert.strictEqual(MineralRegistry.hasProductionModel(mineralId), false);
    });

    test(`${config.displayName}: statusLabel indicates framework ready`, () => {
        assert.ok(
            config.statusLabel.includes('Framework Ready') || config.statusLabel.includes('Not Yet Trained'),
            `Expected statusLabel to indicate framework ready, got: ${config.statusLabel}`
        );
    });
});

// --- Test: getTrainedMinerals returns only Manganese ---
test('getTrainedMinerals returns exactly [Manganese]', () => {
    const trained = MineralRegistry.getTrainedMinerals();
    assert.strictEqual(trained.length, 1);
    assert.strictEqual(trained[0].id, 'manganese');
});

// --- Test: getUntrainedMinerals returns exactly 6 ---
test('getUntrainedMinerals returns exactly 6 minerals', () => {
    const untrained = MineralRegistry.getUntrainedMinerals();
    assert.strictEqual(untrained.length, 6);
    untrained.forEach(m => {
        assert.strictEqual(m.status, 'framework_ready');
    });
});

// --- Test: No fake data exists for untrained minerals ---
test('No Manganese data paths leaked to other minerals', () => {
    const mn = MineralRegistry.getMineral('manganese');
    untrainedMinerals.forEach(id => {
        const m = MineralRegistry.getMineral(id);
        // Ensure no untrained mineral shares Manganese's data paths
        assert.notStrictEqual(m.modelPath, mn.modelPath);
        assert.notStrictEqual(m.gridPath, mn.gridPath);
        assert.notStrictEqual(m.zonesPath, mn.zonesPath);
        assert.notStrictEqual(m.rasterPath, mn.rasterPath);
    });
});

console.log(`\n================================================================`);
console.log(`MULTI-MINERAL SMOKE TEST: ${passed} / ${total} tests passed (${Math.round(passed/total*100)}%)`);
console.log(`================================================================\n`);

process.exit(passed === total ? 0 : 1);
