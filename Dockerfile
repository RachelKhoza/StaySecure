
FROM node:14

# Set the Working Directory
WORKDIR /usr/src/app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the Rest of the Application code
COPY . .

# Install ts-node globaly
RUN npm install -g ts-node

# Set the default cmd
CMD ["sh", "start.sh"]