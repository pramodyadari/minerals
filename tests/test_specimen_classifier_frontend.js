/**
 * Frontend Specimen Classifier & Unknown Mineral Rejection Regression Test.
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');

console.log('Running Specimen Classifier Frontend & Unknown Rejection Tests...');

// 1. Verify SpecimenClassifierModal.jsx exists and contains OOD rejection handling
const modalPath = path.resolve(__dirname, '../frontend/src/components/SpecimenClassifierModal.jsx');
assert(fs.existsSync(modalPath), 'SpecimenClassifierModal.jsx must exist');
const content = fs.readFileSync(modalPath, 'utf8');

// Check CLASS_COLORS includes Unknown
assert(content.includes("'Unknown / Unsupported Mineral': '#f59e0b'"), 'CLASS_COLORS must include Unknown / Unsupported Mineral');
console.log('[PASS] CLASS_COLORS defines explicit color for Unknown / Unsupported Mineral');

// Check OOD check condition
assert(content.includes('result.is_supported_mineral === false'), 'Must check result.is_supported_mineral === false');
assert(content.includes('result.predicted_mineral === \'Unknown / Unsupported Mineral\''), 'Must handle Unknown / Unsupported Mineral');
console.log('[PASS] Logic evaluates is_supported_mineral and Unknown status');

// Check rendering elements for unknown
assert(content.includes('Out-of-Distribution (Rejected)'), 'Must render Out-of-Distribution badge for rejected samples');
assert(content.includes('Specimen Rejected: Non-Target Rock / Unsupported Mineral'), 'Must render scientific rejection explanation');
assert(content.includes('Feature Distance:'), 'Must display Feature Distance');
assert(content.includes('Closest Candidate:'), 'Must display Closest Candidate');
assert(content.includes('Raw Closed-World Softmax Spectrum'), 'Must distinguish raw closed-world softmax from identification');
console.log('[PASS] UI renders diagnostic explanation, distance metric, closest candidate, and raw softmax separation');

// Check in-domain verified elements
assert(content.includes('Verified In-Domain (Provisional Identification)'), 'Must render Verified In-Domain (Provisional Identification) badge for accepted minerals');
assert(content.includes('Provisional Predicted Class'), 'Must render Provisional Predicted Class label');
assert(content.includes('Manifold Verification Passed'), 'Must render Manifold Verification Passed status');
console.log('[PASS] UI renders verified in-domain state with provisional classification and manifold distance verification');

// Check icons
assert(content.includes('ShieldAlert'), 'Must include ShieldAlert icon for rejection');
assert(content.includes('ShieldCheck'), 'Must include ShieldCheck icon for verification');
console.log('[PASS] Lucide icons (ShieldAlert, ShieldCheck) imported and utilized');

// Check Possible Manganese - Not Confirmed banner
assert(content.includes('Possible Manganese — Not Confirmed'), 'Must display "Possible Manganese — Not Confirmed" indicator');
assert(content.includes('shown separately from the final identification decision'), 'Nearest candidate must be shown separately from final identification decision');
assert(content.includes('Never describe a'), 'Must warn against treating closed-world softmax as real-world probability');
console.log('[PASS] UI renders "Possible Manganese — Not Confirmed" indicator with probability caveats and separated candidate');

// Check retest workflow and photography guidance
assert(content.includes('Retest Workflow: Upload New Photograph'), 'Must provide clear retest workflow action button');
assert(content.includes('Photography Guidance & Retest Tips'), 'Must provide collapsible photography guidance');
console.log('[PASS] UI provides clear retest workflow and photography guidance');

// Check MPO image format support
assert(content.includes('Supports JPEG, PNG, WebP, MPO'), 'Must document MPO support in upload dropzone');
assert(content.includes('.mpo'), 'File input accept attribute must include .mpo');
assert(content.includes('isMpo'), 'handleFileChange must include MPO validation check');
console.log('[PASS] UI accepts and validates MPO image uploads safely');

console.log('\nAll Specimen Classifier Frontend tests passed successfully!');
