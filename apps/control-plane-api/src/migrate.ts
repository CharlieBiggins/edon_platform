import { readFile, readdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
const loadPg = new Function('specifier', 'return import(specifier)') as (specifier: string) => Promise<{ Pool: new (options: { connectionString: string }) => { query: (sql: string) => Promise<unknown>; end: () => Promise<void> } }>;
const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) throw new Error('DATABASE_URL is required');
const pg = await loadPg('pg'); const pool = new pg.Pool({ connectionString: databaseUrl });
try { const root = dirname(new URL(import.meta.url).pathname); const migrationDir = join(root, '../../../../apps/control-plane-api/migrations'); for (const file of (await readdir(migrationDir)).filter(name => name.endsWith('.sql')).sort()) await pool.query(await readFile(join(migrationDir, file), 'utf8')); } finally { await pool.end(); }
