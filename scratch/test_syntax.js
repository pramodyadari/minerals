const fs = require('fs');
const path = require('path');
const vm = require('vm');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');

// Check script files for syntax errors
const scriptFiles = [
    'js/mineral-registry.js',
    'js/geo.js',
    'js/data.js',
    'js/locations.js',
    'js/prospectivity.js',
    'js/zones.js',
    'js/production.js',
    'js/xai.js',
    'js/evidence.js',
    'js/ranking.js',
    'js/map.js',
    'js/visual3d.js',
    'app.js'
];

console.log('Checking script files syntax...');
for (const sf of scriptFiles) {
    try {
        const code = fs.readFileSync(path.join(__dirname, '..', sf), 'utf8');
        new vm.Script(code, { filename: sf });
        console.log(`[OK] ${sf}`);
    } catch (e) {
        console.error(`[SYNTAX ERROR] ${sf}:`, e.message);
    }
}
