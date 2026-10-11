const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Create a browser-like global environment
const window = {
    location: { hash: '#dashboard' },
    addEventListener: (ev, fn) => {
        if (ev === 'DOMContentLoaded') setTimeout(fn, 10);
    },
    removeEventListener: () => {},
    scrollTo: () => {},
    print: () => {},
    IntersectionObserver: class {
        constructor() {}
        observe() {}
        disconnect() {}
    }
};

const document = {
    getElementById: (id) => {
        return {
            id,
            value: id === 'mineral-select' ? 'manganese' : '',
            textContent: '',
            style: {},
            classList: { add: () => {}, remove: () => {}, toggle: () => {} },
            addEventListener: (ev, fn) => {},
            querySelectorAll: () => [],
            setAttribute: () => {},
            getAttribute: () => null,
            appendChild: () => {}
        };
    },
    querySelectorAll: (sel) => [],
    querySelector: (sel) => null,
    createElement: (tag) => ({
        style: {},
        textContent: '',
        appendChild: () => {}
    }),
    head: { appendChild: () => {} },
    body: { appendChild: () => {} },
    addEventListener: (ev, fn) => {}
};

const sandbox = {
    window,
    document,
    navigator: { userAgent: 'node' },
    location: window.location,
    console,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    Math,
    Date,
    JSON,
    parseFloat,
    parseInt,
    isNaN,
    isFinite,
    Array,
    Object,
    String,
    Number,
    Boolean,
    RegExp,
    Error,
    Promise,
    self: window,
    this: window
};
sandbox.window.window = sandbox.window;
sandbox.window.document = sandbox.document;

vm.createContext(sandbox);

const scripts = [
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

console.log('Executing all scripts in browser-like context...');
for (const s of scripts) {
    try {
        const code = fs.readFileSync(path.join(__dirname, '..', s), 'utf8');
        vm.runInContext(code, sandbox, { filename: s });
        console.log(`[EXEC OK] ${s}`);
    } catch (e) {
        console.error(`[EXEC ERROR] in ${s}:`, e);
    }
}
