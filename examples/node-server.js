import http from 'node:http';
import { env, envInt, nodeBaseUrl, publicConfig } from './env.mjs';
import { parseUri } from '../js/index.js';

const API_PATH = env('URIDEMO_API_PATH');
const CONFIG_PATH = env('URIDEMO_CONFIG_PATH');
const HEALTH_PATH = env('URIDEMO_HEALTH_PATH');
const HOST = env('URIDEMO_NODE_HOST');
const PORT = envInt('URIDEMO_NODE_PORT');

function writeJson(res, status, data) {
  const raw = JSON.stringify(data, null, 2);
  res.writeHead(status, {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Origin': '*',
    'Content-Length': Buffer.byteLength(raw),
    'Content-Type': 'application/json; charset=utf-8',
  });
  res.end(raw);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? '/', `http://${HOST}:${PORT}`);
  if (req.method === 'OPTIONS') {
    writeJson(res, 204, {});
    return;
  }
  if (req.method === 'GET' && url.pathname === HEALTH_PATH) {
    writeJson(res, 200, { ok: true, service: 'uridemo-node' });
    return;
  }
  if (req.method === 'GET' && url.pathname === CONFIG_PATH) {
    writeJson(res, 200, { ok: true, config: publicConfig() });
    return;
  }
  if (req.method !== 'POST' || url.pathname !== API_PATH) {
    writeJson(res, 404, { ok: false, error: 'not found' });
    return;
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
  const parsed = parseUri(body.uri);
  writeJson(res, 200, { ok: true, parsed, payload: body.payload ?? {} });
});

server.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    console.error(`node demo cannot bind ${HOST}:${PORT}: address already in use`);
    process.exit(1);
  }
  throw error;
});

server.listen(PORT, HOST, () => {
  console.log(`node demo listening on ${nodeBaseUrl()}`);
});
