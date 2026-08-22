const { execSync } = require('child_process');
const { concurrently } = require('concurrently');

// Kill leftovers on OUR ports only (3002 frontend, 8003 backend).
// NOTE: 3000/3001/8001/8002/8765 belong to TradeStack / option-trading-bot —
// do NOT touch those, their dev.js would kill this app.
function killPort(port) {
  try {
    execSync(
      `powershell -Command "$(Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -ExpandProperty OwningProcess -Unique) | ForEach-Object { Stop-Process -Id $_ -Force }"`,
      { stdio: 'ignore', timeout: 3000 },
    );
  } catch (_) {}
}

killPort(8003);
killPort(3002);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  await sleep(1000);

  const isProd = process.argv.includes('--prod');

  const { result } = concurrently(
    [
      {
        command: 'powershell -Command "$env:PORT=3002; bun run dev"',
        name: 'next',
        cwd: 'frontend',
        prefixColor: 'blue',
      },
      {
        command: '.\\venv\\Scripts\\python server.py',
        name: 'py',
        cwd: 'backend',
        prefixColor: 'yellow',
      },
    ],
    {
      prefix: 'name',
      killOthersOnFail: true,
    },
  );

  result.catch(() => process.exit(1));
})();