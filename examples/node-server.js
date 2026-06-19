import http from 'node:http';
import { parseUri } from '../js/index.js';

const server = http.createServer(async (req, res) => {
  if (req.method !== 'POST' || req.url !== '/api/dispatch') {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'not found' }));
    return;
  }
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
  const parsed = parseUri(body.uri);
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ ok: true, parsed, payload: body.payload ?? {} }));
});

server.listen(3000, () => {
  console.log('node demo listening on http://127.0.0.1:3000');
});
