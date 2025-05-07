# Trimble Media Coverage Tracker

A FastAPI application for tracking and analyzing media coverage for Trimble.

## Project Structure

This project follows the standard FastAPI project structure:

```
├── app/                     # Main application package
│   ├── core/                # Core functionality (config, security, etc.)
│   ├── db/                  # Database connection and queries
│   ├── models/              # Database models (if using ORM)
│   ├── routers/             # API routes
│   ├── schemas/             # Pydantic models (request/response schemas)
│   ├── services/            # Business logic
│   └── utils/               # Utility functions
├── tests/                   # Test directory
├── main.py                  # Application entry point
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## Features

- Process hyperlinks from Excel sheets to analyze media coverage
- Extract text from web articles and images
- Categorize articles based on their content
- Generate reports in Excel format

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run tests using pytest:

```bash
pytest
```

## API Endpoints

- `POST /api/v1/media/agents/all/messages` - Send messages to all assistants
- `POST /api/v1/media/agents/{assistant_id}/messages` - Send a message to a specific assistant
- `POST /api/v1/media/agents/{assistant_id}/sessions/{session_id}/images` - Upload an image
- `POST /api/v1/media/process-hyperlinks` - Process hyperlinks from Excel and store responses 