import db from '../../LovelyProject/src/db';

// Use parameterized queries to avoid SQL injection
export const addUser = async (
  username: string, 
  name: string, 
  location: string
) => {
  console.log(`Inserting users: ${username}, ${name}, ${location}`);
  return db.none(
    'INSERT INTO users(username, name, location) VALUES($1, $2, $3)',
    [username, name, location]
  );
};

// Function to add a language for a user to the database
export const addLanguage = async (userId: number, language: string) => {
  console.log(`Inserting language: ${language} for user ID: ${userId}`);
  return db.none(
    'INSERT INTO languages(user_id, language) VALUES($1, $2)', 
    [userId, language]
  );
};

// Function to get all users from the db
export const getUsers = async () => {
  console.log('Fetching all users');
  return db.any('SELECT * FROM users');
};

// Function to get users by location from the db
export const getUsersByLocation = async (location: string) => {
  console.log(`Fetching users by location: ${location}`);
  return db.any(
    'SELECT * FROM users WHERE location = $1',
    [location]
  );
};