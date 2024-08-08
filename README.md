# LovelyProject

A command-line application to fetch GitHub user information and store it in PostgreSQL.

## Table of Contents

- [LovelyProject](#lovelyproject)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Environment Variables](#environment-variables)
  - [Running with Docker](#running-with-docker)
  - [Security Considerations](#security-considerations)
  - [License](#license)

## Introduction

LovelyProject is a command-line application built with Node.js and TypeScript. It fetches information about a given GitHub user using the GitHub API and stores it in a PostgreSQL database. You can also list users and query them by location.

## Features

- Fetch GitHub user information and store it in a PostgreSQL database.
- List all stored users.
- Query users by location.
- Secure against SQL injection and other common vulnerabilities.

## Requirements

- Node.js (v14 or later)
- PostgreSQL
- Docker 

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME.git
   cd YOUR_REPOSITORY_NAME

2.	Install dependencies:

    npm install

3.	Create a .env file in the root directory and add the following environment variables:
Used Docker and downloaded a postgres image then ran the container
eg . 
$ docker run --name some-postgres -p 5432:5432 -e POSTGRES_PASSWORD=MyPass -d postgres


DATABASE_URL=postgres://postgres:YOURPASSWORD@imagename:5432/DBNAME
GITHUB_TOKEN=your_github_token
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOURPASS
POSTGRES_DB=DBNAME


## Usage

Fetch GitHub User Information

To fetch and store a GitHub user’s information, run:

./start.sh fetch <github_username>

List All Users

To list all stored users, run:

./start.sh list

Query Users by Location

To list users by a specific location, run:


Env Variables

Ensure the following environment variables are set in your .env file:

	•	DATABASE_URL: The URL for connecting to the PostgreSQL database.
	•	GITHUB_TOKEN: Your GitHub personal access token.
	•	POSTGRES_USER: The PostgreSQL user.
	•	POSTGRES_PASSWORD: The PostgreSQL user’s password.
	•	POSTGRES_DB: The name of the PostgreSQL database.

## Running with Docker

Build and Start Containers

To build and start the Docker containers, run:

docker-compose up --build -d

Stop Containers

To stop the Docker containers, run:
docker-compose down

## Linting

To ensure the code adheres to best practices and style guidelines, we use ESLint. Linting helps in maintaining code quality and consistency.

### Run ESLint

1. **Lint the code**:

    ```bash
    npm run lint
    ```

2. **Fix linting errors**:

    ESLint will display any errors or warnings in the code. Fix these issues according to the provided messages. For example, if you encounter a `max-len` error, you might need to break long lines into multiple lines.


## Security Considerations

	•	SQL Injection Protection: Parameterized queries are used to protect against SQL injection.
	•	Environment Variables: Sensitive information is stored in environment variables.
