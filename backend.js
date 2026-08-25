const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Backend-only helpers (frontend untouched):
//   bun run kb  -> KILL whatever is listening on our backend port (8003)
//   bun run sb  -> START a fresh backend in this terminal (foreground logs)
//
// SAFETY RULE (strict): hum sirf APNA backend marte hain. Ownership 2 tarike
// se prove hota hai, warna SKIP:
//   1. PID-FILE  : data/backend.pid (start-mode ne khud likha) + wohi PID
//                  8003 pe listen kar raha ho -> trusted
//   2. PATH MARKER: process ka ExecutablePath/CommandLine 'at_trading' +
//                  'server.py' contain kare
// Koi aur project/bot ka process 8003 pe mila -> SKIP + warning, kill NAHI.
//
// NOTE: 3000/3001/8001/8002/8765 belong to TradeStack / option-trading-bot —
// do NOT touch those ports (same rule as dev.js).

const PORT = 8003;
const ROOT = __dirname;
const PYTHON = path.join(ROOT, 'backend', 'venv', 'Scripts', 'python.exe');
const SERVER = path.join(ROOT, 'backend', 'server.py');
const PID_FILE = path.join(ROOT, 'data', 'backend.pid');

function ps(cmd) {
  return execSync(`powershell -Command "${cmd}"`, { encoding: 'utf8', timeout: 5000 }).trim();
}

function listeningPids(port) {
  try {
    return ps(
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
    const raw = ps(
      `(Get-CimInstance Win32_Process -Filter 'ProcessId=${pid}' | Select-Object CommandLine, ExecutablePath | ConvertTo-Json -Compress)`,
    );
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
}

function readPidFile() {
  try {
    const v = parseInt(fs.readFileSync(PID_FILE, 'utf8').trim(), 10);
    return Number.isFinite(v) ? v : null;
  } catch (_) {
    return null;
  }
}

function writePidFile(pid) {
  try {
    fs.mkdirSync(path.dirname(PID_FILE), { recursive: true });
    fs.writeFileSync(PID_FILE, String(pid));
  } catch (_) {}
}

function clearPidFile() {
  try {
    fs.unlinkSync(PID_FILE);
  } catch (_) {}
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
  const trusted = readPidFile();

  if (!pids.length) {
    if (trusted != null) clearPidFile();
    console.log(`[kb] port ${port} already free ✓`);
    return;
  }

  let killed = 0;
  for (const pid of pids) {
    // 1) PID-FILE trust: humne khud start kiya tha
    if (trusted != null && pid === trusted) {
      stopPid(pid);
      console.log(`[kb] killed PID ${pid} (pidfile-trusted apna backend) ✓`);
      killed++;
      continue;
    }
    // 2) PATH MARKER: absolute at_trading + server.py
    const info = procInfo(pid);
    const hay = `${info.CommandLine || ''} ${info.ExecutablePath || ''}`.toLowerCase();
    if (hay.includes('at_trading') && hay.includes('server.py')) {
      stopPid(pid);
      console.log(`[kb] killed PID ${pid} (at_trading marker match) ✓`);
      killed++;
      continue;
    }
    const extra =
      trusted == null
        ? ' (tip: backend ko bun run sb se start karo toh ownership auto-proof hota hai)'
        : '';
    console.log(
      `[kb] SKIP PID ${pid} — HAMARA NAHI${extra}: ${(info.CommandLine || '').slice(0, 90)}`,
    );
  }

  if (!killed) {
    console.log('[kb] koi APNA trusted process nahi mila — doosre projects touch nahi hue');
  } else if (trusted != null) {
    // venv launcher (pidfile wala) real python ko spawn karke zinda reh sakta
    // hai — usko bhi clean karo, par sirf tab jab wo APNA ho (exe path check)
    const info = procInfo(trusted);
    const exe = `${info.ExecutablePath || ''}`.toLowerCase();
    if (exe.includes('at_trading') && !listeningPids(port).includes(trusted)) {
      stopPid(trusted);
      console.log(`[kb] launcher PID ${trusted} cleaned ✓`);
    }
    clearPidFile();
  }
}

function portBusyPid(port) {
  try {
    return ps(
      `(Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess)`,
    );
  } catch (_) {
    return '';
  }
}

const mode = process.argv[2];

if (mode === 'kill') {
  killPort(PORT);
} else if (mode === 'start') {
  const busy = portBusyPid(PORT);
  if (busy) {
    console.log(`[sb] port ${PORT} busy (PID ${busy}). Pehle 'bun run kb' chala.`);
    process.exit(1);
  }
  console.log(`[sb] starting backend on :${PORT} (Ctrl+C = clean exit) ...`);
  const child = spawn(PYTHON, [SERVER], {
    cwd: path.join(ROOT, 'backend'),
    stdio: 'inherit',
  });
  writePidFile(child.pid);
  child.on('exit', (code) => {
    clearPidFile();
    console.log(`[sb] backend exited (${code})`);
  });
} else {
  console.log('Usage: bun run kb (kill apna backend) | bun run sb (start backend)');
}
