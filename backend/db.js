import 'dotenv/config';
import pkg from 'pg';
const { Pool } = pkg;

const pool = new Pool({
  user: process.env.PGUSER || 'postgres',
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'finxl_platform',
  password: process.env.PGPASSWORD,
  port: Number(process.env.PGPORT) || 5432,
  keepAlive: true, // stops idle connections being dropped by the network
});

pool.on('connect', () => {
  console.log('Connected to PostgreSQL Database successfully!');
});

// A dropped idle connection must not take the whole API down: the pool discards it and opens a new one
pool.on('error', (err) => {
  console.error('Database connection dropped (will reconnect on next request):', err.message);
});

// Test the connection immediately on startup
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('Connection test query failed:', err.message);
    console.error('Check PGPASSWORD in backend/.env and that the postgresql service is running.');
  } else {
    console.log('Database test query successful at:', res.rows[0].now);
  }
});

export default pool;