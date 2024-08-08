import pgPromise from 'pg-promise';
import dotenv from 'dotenv';

dotenv.config(); // Load env vars

const pgp = pgPromise();

// here im using a confige object to avoid string 
//Interpolaion which can be a Security risk
const dbConfig = {
  connectionString: process.env.DATABASE_URL,
  ssl: false // Disable SSL this is a security 
  //risk for Prod Env and should be set to true in Prod
};

const db = pgp(dbConfig);

export default db;