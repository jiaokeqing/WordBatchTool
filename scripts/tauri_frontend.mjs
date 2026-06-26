import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const mode = process.argv[2];
const argsByMode = {
  dev: ['run', 'dev', '--', '--host', '127.0.0.1', '--port', '5173'],
  build: ['run', 'build'],
};

const args = argsByMode[mode];
if (!args) {
  console.error('Usage: node ../scripts/tauri_frontend.mjs <dev|build>');
  process.exit(1);
}

const scriptDir = dirname(fileURLToPath(import.meta.url));
const frontendDir = join(scriptDir, '..', 'frontend');
const env = Object.fromEntries(
  Object.entries(process.env).filter(([key, value]) => key && !key.startsWith('=') && !key.includes('\0') && !String(value).includes('\0')),
);

const command = process.platform === 'win32' ? process.env.ComSpec || 'cmd.exe' : 'pnpm';
const commandArgs = process.platform === 'win32' ? ['/d', '/s', '/c', ['pnpm.cmd', ...args].join(' ')] : args;

execFileSync(command, commandArgs, {
  cwd: frontendDir,
  env: { ...env, VITE_API_BASE: 'http://127.0.0.1:8765' },
  stdio: 'inherit',
});
