import pkg from 'pg';
const { Pool } = pkg;

const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'finxl_platform',
  password: '1234', // Make sure this matches your pgAdmin password
  port: 5432,
});

pool.on('connect', () => {
  console.log('Connected to PostgreSQL Database successfully!');
});

// Catch connection errors instead of crashing silently
pool.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
  process.exit(-1);
});

// Test the connection immediately on startup
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.error('Connection test query failed:', err.message);
  } else {
    console.log('Database test query successful at:', res.rows[0].now);
  }
});

export default pool;