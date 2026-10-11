const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const testsDir = __dirname;
const files = fs.readdirSync(testsDir).filter(f => f.endsWith('.js') && f.startsWith('test_') && f !== 'run_all_js_tests.js');

let totalPassMarks = 0;
let totalFailedFiles = 0;

console.log('Running JavaScript test suite...');
for (const file of files) {
    const fullPath = path.join(testsDir, file);
    try {
        const out = execSync(`node "${fullPath}"`, { encoding: 'utf8', stdio: 'pipe' });
        const passMatches = out.match(/\[PASS\]/gi);
        const count = passMatches ? passMatches.length : 0;
        totalPassMarks += count;
        console.log(`PASS: ${file} (${count} tests passed)`);
    } catch (err) {
        console.error(`FAIL: ${file}`);
        console.error(err.stdout || err.stderr || err.message);
        totalFailedFiles += 1;
    }
}

console.log(`\n================================================================`);
console.log(`JavaScript Summary: ${totalPassMarks} tests passed across ${files.length} test files. Failed files: ${totalFailedFiles}`);
console.log(`================================================================`);

if (totalFailedFiles > 0) {
    process.exit(1);
}
