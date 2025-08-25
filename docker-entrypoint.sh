#!/bin/bash
set -e

# Create data directory if it doesn't exist
mkdir -p /app/data

# Set proper permissions
chmod -R 755 /app/data

# Start the application
exec "$@"
