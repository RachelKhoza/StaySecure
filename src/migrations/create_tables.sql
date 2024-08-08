CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255),
  location VARCHAR(255)
);

CREATE TABLE languages (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  language VARCHAR(255)
);