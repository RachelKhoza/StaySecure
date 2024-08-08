
# Load environment variables from .env file
export $(grep -v '^#' .env | xargs)

# Check if command argument is provided
if [ -z "$1" ]; then
  echo "Error: No command provided."
  echo "Usage: ./start.sh <command> [arguments]"
  exit 1
fi

# Verify the environment variables are loaded
echo "DATABASE_URL: $DATABASE_URL"
echo "GITHUB_TOKEN: $GITHUB_TOKEN"

# Run the TypeScript script with the given command
npx ts-node src/index.ts "$@"