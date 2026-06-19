import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const ENV_PATH = path.join(ROOT, '.env');

let loaded = false;
const dotenvKeys = new Set();

function parseLine(line) {
  const stripped = line.trim();
  if (!stripped || stripped.startsWith('#') || !stripped.includes('=')) return null;
  const splitAt = stripped.indexOf('=');
  const key = stripped.slice(0, splitAt).trim();
  let value = stripped.slice(splitAt + 1).trim();
  if (!key) return null;
  if (value.length >= 2 && value[0] === value[value.length - 1] && ['"', "'"].includes(value[0])) {
    value = value.slice(1, -1);
  }
  return [key, value];
}

export function loadEnv({ override = false } = {}) {
  if (loaded && !override) return process.env;
  if (fs.existsSync(ENV_PATH)) {
    const lines = fs.readFileSync(ENV_PATH, 'utf8').split(/\r?\n/);
    for (const line of lines) {
      const parsed = parseLine(line);
      if (!parsed) continue;
      const [key, value] = parsed;
      dotenvKeys.add(key);
      if (override || process.env[key] === undefined) {
        process.env[key] = value;
      }
    }
  }
  loaded = true;
  return process.env;
}

export function env(name, defaultValue = undefined) {
  loadEnv();
  const value = process.env[name] ?? defaultValue;
  if (value === undefined) {
    throw new Error(`missing ${name} in ${ENV_PATH}`);
  }
  return value;
}

export function envInt(name, defaultValue = undefined) {
  return Number.parseInt(env(name, defaultValue === undefined ? undefined : String(defaultValue)), 10);
}

export function envFloat(name, defaultValue = undefined) {
  return Number.parseFloat(env(name, defaultValue === undefined ? undefined : String(defaultValue)));
}

export function baseUrl() {
  loadEnv();
  return process.env.URIDEMO_BASE_URL ?? `http://${env('URIDEMO_PUBLIC_HOST')}:${env('URIDEMO_PORT')}`;
}

export function nodeBaseUrl() {
  loadEnv();
  return process.env.URIDEMO_NODE_BASE_URL ?? `http://${env('URIDEMO_NODE_HOST')}:${env('URIDEMO_NODE_PORT')}`;
}

export function publicConfig() {
  loadEnv();
  return Object.fromEntries(
    [...dotenvKeys]
      .filter((key) => key.startsWith('URIDEMO_') || key.startsWith('URI_'))
      .sort()
      .map((key) => [key, process.env[key]]),
  );
}
