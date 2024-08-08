import pgPromise from 'pg-promise';
import dotenv from 'dotenv';

dotenv.config(); // Load environment variables

const pgp = pgPromise();

const dbConfig = {
  connectionString: process.env.DATABASE_URL,
  ssl: false // Disable SSL if not supported by the server
};

const db = pgp(dbConfig);

async function testConnection() {
  try {
    const result = await db.one('SELECT 1 as value');
    console.log('Database connection successful:', result);
  } catch (error) {
    console.error('Database connection failed:', error);
  } finally {
    pgp.end(); // Close the connection pool
  }
}

testConnection();