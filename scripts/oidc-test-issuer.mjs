import { createServer } from 'node:http';
const jwks = { keys: [{ kty: 'RSA', kid: 'ci-test-key-v1', use: 'sig', alg: 'RS256', n: 'ci-placeholder', e: 'AQAB' }] };
const server = createServer((request, response) => { response.setHeader('content-type', 'application/json'); if (request.url === '/.well-known/jwks.json') return response.end(JSON.stringify(jwks)); response.statusCode = 404; response.end(JSON.stringify({ error: 'not_found' })); });
server.listen(8899, '127.0.0.1');
process.on('SIGTERM', () => server.close(() => process.exit(0)));
