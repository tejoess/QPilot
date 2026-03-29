import { neon } from '@neondatabase/serverless';
import { drizzle, NeonHttpDatabase } from 'drizzle-orm/neon-http';
import * as schema from './db/schema';

let _db: NeonHttpDatabase<typeof schema> | null = null;

export function getDb() {
    if (!_db) {
        const sql = neon(process.env.DATABASE_URL!);
        _db = drizzle(sql, { schema });
    }
    return _db;
}

// For backward compatibility — use as a getter
export const db = new Proxy({} as NeonHttpDatabase<typeof schema>, {
    get(_target, prop) {
        return (getDb() as any)[prop];
    },
});
