# Docker Setup for Media Coverage Tracker

This document provides instructions for running the Media Coverage Tracker application using Docker.

## Prerequisites

- Docker Desktop installed on your system
- Docker Compose (included with Docker Desktop)

## Quick Start

### 1. Build and Run with Docker Compose

```bash
# Build and start the application
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

The API will be available at:
- **API**: http://localhost:8002
- **API Documentation**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

### 2. Using Docker directly

```bash
# Build the image
docker build -t media-coverage-tracker .

# Run the container
docker run -p 8002:8002 -v $(pwd)/data:/app/data media-coverage-tracker
```

## Configuration

### Environment Variables

You can customize the application by setting environment variables:

```bash
# Example with custom settings
docker run -p 8002:8002 \
  -e PYTHONUNBUFFERED=1 \
  -v $(pwd)/data:/app/data \
  media-coverage-tracker
```

### Volume Mounts

The application uses the following volumes:

- `/app/data` - For storing processed data and temporary files
- `/app/Trimble_Media_Coverage_Tracker.xlsx` - The main Excel file

## Production Deployment

For production deployment with Nginx reverse proxy:

```bash
# Start with production profile (includes Nginx)
docker-compose --profile production up --build -d
```

This will:
- Run the API on port 8002 (internal)
- Run Nginx on port 80 (external)
- Handle CORS properly
- Provide load balancing capabilities

## Development

### Hot Reload

The Docker setup includes hot reload for development. Any changes to your Python files will automatically restart the server.

### Debugging

To run the container with debugging capabilities:

```bash
docker-compose up --build
# Logs will be displayed in real-time
```

To view logs of a running container:

```bash
docker-compose logs -f media-coverage-api
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Make sure port 8002 is not being used by another application
2. **Permission issues**: Ensure Docker has permission to access your project directory
3. **Excel file not found**: Make sure `Trimble_Media_Coverage_Tracker.xlsx` exists in the project root

### Health Check

The application includes a health check endpoint. You can verify it's running:

```bash
curl http://localhost:8002/docs
```

### Container Shell Access

To access the container shell for debugging:

```bash
docker-compose exec media-coverage-api bash
```

## Stopping the Application

```bash
# Stop and remove containers
docker-compose down

# Stop, remove containers, and remove volumes
docker-compose down -v
```

## Building for Different Architectures

If you need to build for different architectures (e.g., ARM64 for Apple Silicon):

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t media-coverage-tracker .
```
