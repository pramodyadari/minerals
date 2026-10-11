const { spawn } = require('child_process');
const http = require('http');

async function main() {
    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless',
        '--disable-gpu',
        '--window-size=1280,900',
        '--remote-debugging-port=9226',
        '--user-data-dir=' + require('os').tmpdir() + '\\chrome-debug-click',
        'http://127.0.0.1:8085/#dashboard'
    ]);

    await new Promise(r => setTimeout(r, 2000));

    http.get('http://127.0.0.1:9226/json', (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', async () => {
            const tabs = JSON.parse(data);
            const pageTab = tabs.find(t => t.type === 'page');
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
                await send('Input.enable');
                await send('Page.enable');

                // Navigate to dashboard and scroll to controls
                await send('Runtime.evaluate', {
                    expression: `(() => {
                        navigateTo('dashboard');
                        const sel = document.getElementById('mineral-select');
                        sel.scrollIntoView({ block: 'center' });
                    })()`
                });

                await new Promise(r => setTimeout(r, 500));

                // Get coordinates of mineral-select
                const coordsRes = await send('Runtime.evaluate', {
                    expression: `(() => {
                        const sel = document.getElementById('mineral-select');
                        const rect = sel.getBoundingClientRect();
                        return {
                            x: Math.round(rect.left + rect.width / 2),
                            y: Math.round(rect.top + rect.height / 2),
                            rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height }
                        };
                    })()`,
                    returnByValue: true
                });

                const coords = coordsRes.result.value;
                console.log('Coordinates of #mineral-select:', coords);

                // Check what element is at (x, y)
                const hitTest = await send('Runtime.evaluate', {
                    expression: `(() => {
                        const el = document.elementFromPoint(${coords.x}, ${coords.y});
                        return el ? { tag: el.tagName, id: el.id, className: el.className } : null;
                    })()`,
                    returnByValue: true
                });
                console.log('Element at point before click:', hitTest.result.value);

                // Add event listeners on mineral-select to track what events fire
                await send('Runtime.evaluate', {
                    expression: `(() => {
                        window._eventsFired = [];
                        const sel = document.getElementById('mineral-select');
                        ['mousedown', 'mouseup', 'click', 'focus', 'change'].forEach(ev => {
                            sel.addEventListener(ev, (e) => {
                                window._eventsFired.push(ev);
                            });
                        });
                    })()`
                });

                // Dispatch real mouse click
                await send('Input.dispatchMouseEvent', {
                    type: 'mousePressed',
                    x: coords.x,
                    y: coords.y,
                    button: 'left',
                    clickCount: 1
                });
                await send('Input.dispatchMouseEvent', {
                    type: 'mouseReleased',
                    x: coords.x,
                    y: coords.y,
                    button: 'left',
                    clickCount: 1
                });

                await new Promise(r => setTimeout(r, 300));

                const eventsRes = await send('Runtime.evaluate', {
                    expression: 'window._eventsFired',
                    returnByValue: true
                });
                console.log('Events fired on #mineral-select:', eventsRes.result.value);

                const activeElRes = await send('Runtime.evaluate', {
                    expression: 'document.activeElement.id',
                    returnByValue: true
                });
                console.log('document.activeElement after click:', activeElRes.result.value);

                ws.close();
                chromeProc.kill();
                process.exit(0);
            };
        });
    });
}

main().catch(console.error);
