import express from 'express';
import cors from 'cors';
import pool from './db.js';

const app = express();

// Allow request body parsing
app.use(express.json());

// Enable CORS for frontend running on port 5173
app.use(cors({
  origin: 'http://localhost:5173',
  methods: ['GET', 'POST'],
  credentials: true
}));

// Login endpoint
app.post('/api/login', async (req, res) => {
  const { email, password } = req.body;

  try {
    const result = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
    
    if (result.rows.length === 0) {
      return res.status(401).json({ success: false, message: 'Invalid email or password' });
    }

    const user = result.rows[0];

    // Simple password validation for dummy users
    if (password !== user.password_hash) {
      return res.status(401).json({ success: false, message: 'Invalid email or password' });
    }

    res.json({
      success: true,
      message: 'Login successful',
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role
      }
    });

  } catch (err) {
    console.error('Database query error:', err.message);
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

const PORT = 5000;
app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});
