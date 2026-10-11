/**
 * ============================================================================
 * AI MINERAL INTELLIGENCE — MULTI-MINERAL FRONTEND INTEGRATION TESTS
 * ============================================================================
 * Test Suite: tests/test_multi_mineral_frontend.js
 * 
 * Verifies:
 *   1. MineralRegistry accurately lists all 7 commodities
 *   2. Manganese is the only genuinely trained mineral
 *   3. All 6 untrained commodities honestly report awaiting training data
 *   4. ExplainableAI strictly isolates XAI feature weights to Manganese
 *   5. ExplainableAI returns empty/unavailable for untrained minerals (Iron, Copper, etc.)
 *   6. ExplainableAI explainProspectivityScore refuses untrained minerals
 *   7. TargetRankingEngine returns 0 targets and explicit untrained message for untrained minerals
 *   8. TargetRankingEngine preserves 20 real candidate zones for Manganese
 *   9. Target comparison refuses untrained minerals without fabricating targets
 *   10. Zero cross-mineral data leakage or shared file paths across commodities
 * ============================================================================
 */

const assert = require('assert');
const MineralRegistry = require('../js/mineral-registry');
const ExplainableAI = require('../js/xai');
const TargetRankingEngine = require('../js/ranking');

let passedTests = 0;
let totalTests = 0;

function runTest(name, fn) {
    totalTests++;
    try {
        fn();
        passedTests++;
        console.log(`[PASS] ${name}`);
    } catch (e) {
        console.error(`[FAIL] ${name}: ${e.message}`);
    }
}

console.log('================================================================');
console.log('TEST SUITE: MULTI-MINERAL FRONTEND INTEGRATION & ISOLATION');
console.log('================================================================\n');

// 1. MineralRegistry structure
runTest('Test 1: MineralRegistry registers all 7 commodities', () => {
    const minerals = MineralRegistry.getAllMinerals();
    assert.strictEqual(minerals.length, 7, 'Must register exactly 7 commodities');
});

// 2. Manganese is the only trained mineral
runTest('Test 2: Manganese is the ONLY genuinely trained commodity', () => {
    const trained = MineralRegistry.getTrainedMinerals();
    assert.strictEqual(trained.length, 1, 'Only 1 mineral should be trained');
    assert.strictEqual(trained[0].id, 'manganese');
    assert.strictEqual(MineralRegistry.isTrained('manganese'), true);
    assert.strictEqual(MineralRegistry.canAnalyze('manganese'), true);
    assert.strictEqual(MineralRegistry.hasZones('manganese'), true);
    assert.strictEqual(MineralRegistry.hasXAI('manganese'), true);
});

// 3. Untrained minerals honestly report framework ready / awaiting data
runTest('Test 3: Untrained commodities (Iron, Copper, Bauxite, Lithium, Coal, Limestone) report awaiting data', () => {
    const untrained = ['iron_ore', 'copper', 'bauxite', 'lithium', 'coal', 'limestone'];
    untrained.forEach(id => {
        const m = MineralRegistry.getMineral(id);
        assert.ok(m, `Mineral ${id} must exist in registry`);
        assert.strictEqual(MineralRegistry.isTrained(id), false);
        assert.strictEqual(MineralRegistry.canAnalyze(id), false);
        assert.strictEqual(MineralRegistry.hasZones(id), false);
        assert.strictEqual(MineralRegistry.hasXAI(id), false);
        assert.strictEqual(m.modelPath, null, `${id} modelPath must be null`);
        assert.strictEqual(m.rasterPath, null, `${id} rasterPath must be null`);
        assert.strictEqual(m.zonesPath, null, `${id} zonesPath must be null`);
    });
});

// 4. XAI Feature importances belong only to Manganese
runTest('Test 4: ExplainableAI returns 10 feature weights for Manganese', () => {
    const mnFeatures = ExplainableAI.getFeatureImportance('manganese');
    assert.strictEqual(mnFeatures.length, 10, 'Manganese must have 10 features');
    const totalWeight = mnFeatures.reduce((acc, f) => acc + f.importancePct, 0);
    assert(Math.abs(totalWeight - 100.0) < 0.2, 'Weights must sum to ~100%');
});

// 5. XAI isolation: Untrained minerals return empty feature list
runTest('Test 5: ExplainableAI returns empty feature array for untrained minerals', () => {
    ['iron_ore', 'copper', 'bauxite', 'lithium'].forEach(min => {
        const feats = ExplainableAI.getFeatureImportance(min);
        assert.strictEqual(feats.length, 0, `XAI features for ${min} must be empty`);
    });
});

// 6. XAI explanation refusal for untrained minerals
runTest('Test 6: ExplainableAI explainProspectivityScore rejects untrained minerals', () => {
    const copperExp = ExplainableAI.explainProspectivityScore(75.0, 'Malanjkhand', 'copper');
    assert.strictEqual(copperExp.isAvailable, false, 'Copper XAI must be marked unavailable');
    assert.strictEqual(copperExp.waterfallSteps.length, 0, 'No waterfall steps for Copper');
    assert.strictEqual(copperExp.features.length, 0, 'No features for Copper');
    assert(copperExp.error.includes('Model not trained'), 'Error must explain model not trained');

    // Manganese remains fully available
    const mnExp = ExplainableAI.explainProspectivityScore(71.0, 'Ghondi', 'manganese');
    assert.strictEqual(mnExp.isAvailable, true, 'Manganese XAI must be available');
    assert.strictEqual(mnExp.features.length, 10, 'Manganese must have 10 features');
    assert.strictEqual(mnExp.waterfallSteps.length, 12, 'Manganese waterfall must have 12 steps');
});

// 7. TargetRankingEngine returns 0 targets and message for untrained minerals
runTest('Test 7: TargetRankingEngine returns 0 candidate zones for untrained commodities', () => {
    ['copper', 'iron_ore', 'bauxite', 'lithium'].forEach(min => {
        const ranking = TargetRankingEngine.getRankedTargets(min);
        assert.strictEqual(ranking.isTrained, false, `${min} ranking must be untrained`);
        assert.strictEqual(ranking.count, 0, `${min} must have 0 candidate targets`);
        assert.strictEqual(ranking.targets.length, 0, `${min} targets array must be empty`);
        assert(ranking.message.includes('Model not trained'), 'Message must state Model not trained');
        assert(ranking.message.includes('Training data required'), 'Message must state Training data required');
    });
});

// 8. TargetRankingEngine preserves Manganese's 20 real zones
runTest('Test 8: TargetRankingEngine preserves 20 real candidate discovery zones for Manganese', () => {
    const mnRanking = TargetRankingEngine.getRankedTargets('manganese');
    assert.strictEqual(mnRanking.isTrained, true, 'Manganese ranking must be active');
    assert.strictEqual(mnRanking.count, 20, 'Manganese must have exactly 20 zones');
    assert.strictEqual(mnRanking.targets[0].rank, 1, 'First target must be Rank 1');
    assert.strictEqual(mnRanking.targets[0].score, 97.6, 'Top score must be 97.6%');
});

// 9. Multi-target comparison refuses untrained minerals
runTest('Test 9: Multi-target comparison safely refuses untrained minerals', () => {
    const copperComp = TargetRankingEngine.compareTargets([67684, 124766], 'copper');
    assert.strictEqual(copperComp.isTrained, false, 'Comparison must be marked untrained');
    assert.strictEqual(copperComp.comparedCount, 0, 'Compared count must be 0');
    assert(copperComp.error.includes('Model not trained'), 'Error must state Model not trained');
});

// 10. Data isolation: zero shared data paths between Manganese and others
runTest('Test 10: Zero path reuse or data leakage between Manganese and any other commodity', () => {
    const mn = MineralRegistry.getMineral('manganese');
    const others = ['iron_ore', 'copper', 'bauxite', 'lithium', 'coal', 'limestone'];
    others.forEach(id => {
        const m = MineralRegistry.getMineral(id);
        assert.notStrictEqual(m.modelPath, mn.modelPath);
        assert.notStrictEqual(m.rasterPath, mn.rasterPath);
        assert.notStrictEqual(m.zonesPath, mn.zonesPath);
    });
});

console.log('\n================================================================');
console.log(`RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round((passedTests / totalTests) * 100)}%)`);
console.log('================================================================\n');

if (passedTests < totalTests) {
    process.exit(1);
}
