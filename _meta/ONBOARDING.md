# Developer Onboarding - ReviewAssist Pro

## Welcome to ReviewAssist Pro

ReviewAssist Pro is an AI-powered review management SaaS platform that helps businesses monitor, analyze, and respond to customer reviews across multiple platforms. This guide will help you get up and running with the development environment.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.9+ (3.11 recommended)
- Node.js 16+ (for any frontend tooling)
- Git
- Docker and Docker Compose (optional but recommended)
- Redis (for real-time features)

## Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/tiarnanlarkin/reviewassist-pro.git
cd reviewassist-pro
cp .env.example .env
# Edit .env with your configuration
```

### 2. Install Dependencies
```bash
make install
# This creates a virtual environment and installs all dependencies
```

### 3. Run Development Server
```bash
make dev
# Application will be available at http://localhost:5000
```

### 4. Access Demo
- URL: http://localhost:5000
- Demo credentials: admin@reviewassist.com / Admin123!

## Project Structure Overview

The project follows a modular Flask application structure:

- `src/models/`: Database models using SQLAlchemy
- `src/routes/`: API endpoints organized by feature
- `src/static/`: Frontend HTML, CSS, and JavaScript
- `tests/`: Test suite using pytest
- `docs/`: Project documentation
- `_meta/`: Project metadata and development guides

## Key Development Commands

```bash
make help          # Show all available commands
make test          # Run test suite
make lint          # Run code linting
make format        # Format code with black and isort
make clean         # Clean build artifacts
```

## Development Workflow

1. **Feature Development**: Create feature branches from main
2. **Code Quality**: Run `make lint` and `make test` before committing
3. **Documentation**: Update `_meta/TASKS.md` for code changes
4. **Architecture**: Add ADRs to `_meta/DECISIONS.md` for major decisions

## Key Technologies

- **Backend**: Flask 3.1.1 with SQLAlchemy ORM
- **Frontend**: Vanilla JavaScript with Tailwind CSS
- **Real-time**: Flask-SocketIO for WebSocket communication
- **Database**: SQLite (dev), PostgreSQL (production)
- **AI**: OpenAI API for response generation
- **Payments**: Stripe integration (in development)

## Environment Configuration

Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY`: Required for AI response generation
- `DATABASE_URL`: Database connection (defaults to SQLite)
- `REDIS_URL`: Redis connection for real-time features
- `SECRET_KEY`: Flask secret key for sessions

## Testing

The project uses pytest for testing:
```bash
make test                    # Run all tests
pytest tests/test_auth.py   # Run specific test file
pytest --cov=src           # Run with coverage
```

## Common Development Tasks

### Adding New Features
1. Create database models in `src/models/`
2. Add API endpoints in `src/routes/`
3. Update frontend in `src/static/`
4. Write tests in `tests/`
5. Update documentation

### Database Changes
Currently using manual schema management. For production, implement Alembic migrations.

### API Development
All API endpoints follow RESTful conventions and return JSON responses. Authentication uses JWT tokens.

## Getting Help

- **Documentation**: Check `/docs/` directory
- **API Reference**: See README.md API documentation section
- **Issues**: Create GitHub issues for bugs or feature requests
- **Architecture**: Review `_meta/DECISIONS.md` for architectural context

## Next Steps

1. Explore the live demo at http://localhost:5000
2. Review the codebase structure and key files
3. Run the test suite to understand testing patterns
4. Check `_meta/TASKS.md` for current development priorities
5. Read `docs/PREPRODUCTION.md` for project context and goals

Welcome to the team! 🚀

