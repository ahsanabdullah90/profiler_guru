#!/bin/sh
set -e

# Profile Guru — Docker entrypoint
# Starts both the Next.js frontend and the FastAPI backend.

echo "Starting Profile Guru backend on port 8000..."
python -m uvicorn main_api:app --host 0.0.0.0 --port 8000 &

echo "Starting Profile Guru frontend on port 3000..."
cd /app/frontend
node node_modules/next/dist/bin/next start -p 3000 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
