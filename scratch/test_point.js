const { spawn } = require('child_process');
const http = require('http');

async function main() {
    const chromeProc = spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', [
        '--headless',
        '--disable-gpu',
        '--window-size=1280,900',
        '--remote-debugging-port=9224',
        '--user-data-dir=' + require('os').tmpdir() + '\\chrome-debug-3',
        'http://127.0.0.1:8085/#dashboard'
    ]);

    await new Promise(r => setTimeout(r, 2000));

    http.get('http://127.0.0.1:9224/json', (res) => {
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
                await new Promise(r => setTimeout(r, 1000));

                await send('Runtime.evaluate', { expression: "navigateTo('dashboard')" });
                await new Promise(r => setTimeout(r, 500));

                const testRes = await send('Runtime.evaluate', {
                    expression: `(() => {
                        return {
                            docScrollH: document.documentElement.scrollHeight,
                            bodyScrollH: document.body.scrollHeight,
                            docClientH: document.documentElement.clientHeight,
                            pageActive: document.getElementById('page-dashboard').className,
                            htmlOverflow: getComputedStyle(document.documentElement).overflow,
                            bodyOverflow: getComputedStyle(document.body).overflow,
                            pageWrapperH: document.querySelector('#page-dashboard .page-wrapper')?.scrollHeight,
                            rect: document.getElementById('mineral-select').getBoundingClientRect()
                        };
                    })()`,
                    returnByValue: true
                });

                console.log(JSON.stringify(testRes.result.value, null, 2));

                ws.close();
                chromeProc.kill();
                process.exit(0);
            };
        });
    });
}

main().catch(console.error);
