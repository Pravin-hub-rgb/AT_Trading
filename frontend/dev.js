const { execSync } = require('child_process');
const { concurrently } = require('concurrently');
const path = require('path');

// Absolute paths so the spawned backend's command line carries 'at_trading' —
// used by the kill-ownership check (see backend.js).
const ROOT = __dirname;
const BACKEND_PYTHON = path.join(ROOT, 'backend', 'venv', 'Scripts', 'python.exe');
const BACKEND_SERVER = path.join(ROOT, 'backend', 'server.py');

// Kill leftovers on OUR ports only (3002 frontend, 8003 backend).
// NOTE: 3000/3001/8001/8002/8765 belong to TradeStack / option-trading-bot —
// do NOT touch those, their dev.js would kill this app.
//
// SAFETY: port 8003 pe sirf APNA backend marte hain — kill se pehle process
// ka ExecutablePath/CommandLine verify hota hai ('at_trading' + 'server.py').
// Foreign process mila toh SKIP. Port 3002 exclusively hamara hai; wahan
// direct kill hota hai par PID + cmdline log hota hai.

function psOut(cmd) {
  return execSync(`powershell -Command "${cmd}"`, { encoding: 'utf8', timeout: 5000 }).trim();
}

function listeningPids(port) {
  try {
    return psOut(
      `(Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -gt 0 } | Select-Object -ExpandProperty OwningProcess -Unique)`,
    )
      .split(/\s+/)
      .filter(Boolean)
      .map(Number);
  } catch (_) {
    return [];
  }
}

function procInfo(pid) {
  try {
    const raw = psOut(
      `(Get-CimInstance Win32_Process -Filter 'ProcessId=${pid}' | Select-Object CommandLine, ExecutablePath | ConvertTo-Json -Compress)`,
    );
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
}

function isOurBackend(info) {
  const hay = `${info.CommandLine || ''} ${info.ExecutablePath || ''}`.toLowerCase();
  return hay.includes('at_trading') && hay.includes('server.py');
}

function stopPid(pid) {
  try {
    execSync(`powershell -Command "Stop-Process -Id ${pid} -Force"`, { stdio: 'ignore', timeout: 3000 });
    return true;
  } catch (_) {
    return false;
  }
}

function killPort(port) {
  const pids = listeningPids(port);
  if (!pids.length) return;

  if (port === 8003) {
    for (const pid of pids) {
      const info = procInfo(pid);
      if (isOurBackend(info)) {
        console.log(`[dev] killed apna backend PID ${pid}`);
        stopPid(pid);
      } else {
        console.log(
          `[dev] SKIP PID ${pid} on 8003 — HAMARA NAHI: ${(info.ExecutablePath || '')} ${(info.CommandLine || '').slice(0, 90)}`,
        );
      }
    }
  } else {
    // 3002 — exclusively our frontend port
    for (const pid of pids) {
      const info = procInfo(pid);
      console.log(`[dev] killing frontend PID ${pid}: ${(info.ExecutablePath || info.CommandLine || '').slice(0, 90)}`);
      stopPid(pid);
    }
  }
}

killPort(8003);
killPort(3002);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitPortFree(port, timeoutMs = 10000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (listeningPids(port).length === 0) return true;
    await sleep(300);
  }
  console.log(`[dev] WARNING: port ${port} still busy after ${timeoutMs}ms — starting anyway`);
  return false;
}

(async () => {
  // Wait until the force-killed processes have FULLY released their ports —
  // starting next while the old one still holds 3002 corrupts the Turbopack
  // cache (symptom: every route 404s after a restart).
  await waitPortFree(8003);
  await waitPortFree(3002);

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
        // dev-py.ps1: auto-restarts the backend on non-zero exit (the sporadic
        // 4294967295 native crash) — clean exits (Ctrl+C) stop the loop.
        // Unquoted like before: space-free absolute paths, cmd.exe-safe.
        command: `powershell -ExecutionPolicy Bypass -File ${ROOT}\\backend\\dev-py.ps1 ${BACKEND_PYTHON} ${BACKEND_SERVER}`,
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