const { spawn } = require('child_process');
const http = require('http');

async function main() {
    const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
    const chromeProc = spawn(chromePath, [
        '--headless',
        '--disable-gpu',
        '--remote-debugging-port=9222',
        '--user-data-dir=' + require('os').tmpdir() + '\\chrome-debug-' + Date.now(),
        'http://127.0.0.1:8085/#dashboard'
    ]);

    await new Promise(r => setTimeout(r, 2000));

    // Get devtools endpoints
    http.get('http://127.0.0.1:9222/json', (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', async () => {
            const tabs = JSON.parse(data);
            const pageTab = tabs.find(t => t.type === 'page');
            if (!pageTab) {
                console.error('No page tab found');
                chromeProc.kill();
                return;
            }

            console.log('Connecting to DevTools WS:', pageTab.webSocketDebuggerUrl);
            const ws = new WebSocket(pageTab.webSocketDebuggerUrl);

            let msgId = 1;
            function send(method, params = {}) {
                return new Promise((resolve) => {
                    const id = msgId++;
                    const handler = (event) => {
                        const resp = JSON.parse(event.data);
                        if (resp.id === id) {
                            ws.removeEventListener('message', handler);
                            resolve(resp.result);
                        }
                    };
                    ws.addEventListener('message', handler);
                    ws.send(JSON.stringify({ id, method, params }));
                });
            }

            ws.onopen = async () => {
                await send('Runtime.enable');
                await send('Console.enable');

                ws.onmessage = (event) => {
                    const parsed = JSON.parse(event.data);
                    if (parsed.method === 'Console.messageAdded') {
                        console.log('[BROWSER CONSOLE]', parsed.params.message.text);
                    }
                    if (parsed.method === 'Runtime.exceptionThrown') {
                        console.error('[BROWSER EXCEPTION]', parsed.params.exceptionDetails);
                    }
                };

                // Wait 1.5s for page to settle
                await new Promise(r => setTimeout(r, 1500));

                // Evaluate diagnosis in page
                const evalResult = await send('Runtime.evaluate', {
                    expression: `(() => {
                        const sel = document.getElementById('mineral-select');
                        if (!sel) return { error: 'No #mineral-select found' };

                        sel.scrollIntoView();
                        const rect = sel.getBoundingClientRect();
                        const center = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
                        const elAtPoint = document.elementFromPoint(center.x, center.y);

                        const computed = window.getComputedStyle(sel);
                        const wrapper = sel.closest('.select-wrapper');
                        const wrapperComputed = wrapper ? window.getComputedStyle(wrapper) : null;
                        const card = sel.closest('.glass-card');
                        const cardComputed = card ? window.getComputedStyle(card) : null;

                        return {
                            id: sel.id,
                            value: sel.value,
                            selectedIndex: sel.selectedIndex,
                            options: Array.from(sel.options).map(o => ({ value: o.value, text: o.text, disabled: o.disabled })),
                            rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
                            pointerEvents: computed.pointerEvents,
                            zIndex: computed.zIndex,
                            display: computed.display,
                            visibility: computed.visibility,
                            opacity: computed.opacity,
                            disabled: sel.disabled,
                            elementFromPoint: elAtPoint ? {
                                tagName: elAtPoint.tagName,
                                id: elAtPoint.id,
                                className: elAtPoint.className
                            } : null,
                            wrapperZIndex: wrapperComputed ? wrapperComputed.zIndex : null,
                            cardZIndex: cardComputed ? cardComputed.zIndex : null
                        };
                    })()`,
                    returnByValue: true
                });

                console.log('Diagnosis Result:\n', JSON.stringify(evalResult.result ? evalResult.result.value : evalResult, null, 2));

                // Now test selecting copper
                const changeTest = await send('Runtime.evaluate', {
                    expression: `(() => {
                        const sel = document.getElementById('mineral-select');
                        sel.value = 'copper';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        const scoreText = document.querySelector('.score-text')?.textContent;
                        const expBanner = document.getElementById('prospectivity-score-explanation')?.textContent?.trim();
                        const btnRunDisabled = document.getElementById('btn-run-analysis')?.disabled;
                        const targetChipStatus = document.getElementById('target-card-status')?.textContent;

                        return {
                            selectedMineralAfterChange: sel.value,
                            scoreText,
                            expBanner,
                            btnRunDisabled,
                            targetChipStatus
                        };
                    })()`,
                    returnByValue: true
                });

                console.log('\nChange to Copper Test:\n', JSON.stringify(changeTest.result ? changeTest.result.value : changeTest, null, 2));

                // Now test selecting manganese back
                const changeBackTest = await send('Runtime.evaluate', {
                    expression: `(() => {
                        const sel = document.getElementById('mineral-select');
                        sel.value = 'manganese';
                        sel.dispatchEvent(new Event('change', { bubbles: true }));

                        const scoreText = document.querySelector('.score-text')?.textContent;
                        const btnRunDisabled = document.getElementById('btn-run-analysis')?.disabled;

                        return {
                            selectedMineralAfterChange: sel.value,
                            scoreText,
                            btnRunDisabled
                        };
                    })()`,
                    returnByValue: true
                });

                console.log('\nChange back to Manganese Test:\n', JSON.stringify(changeBackTest.result ? changeBackTest.result.value : changeBackTest, null, 2));

                ws.close();
                chromeProc.kill();
                process.exit(0);
            };
        });
    });
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
