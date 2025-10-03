# AI Guide - ReviewAssist Pro

## Quick Start for AI Assistants

Read `docs/PREPRODUCTION.md` first for complete project context. GitHub main branch contains working code only.

## Project Context

ReviewAssist Pro is an AI-powered review management SaaS platform built with Flask and modern web technologies. The application helps businesses manage customer reviews across multiple platforms with AI-generated responses, real-time analytics, and automation workflows.

## Key Development Guidelines

### Architecture
- **Backend**: Flask application with SQLAlchemy ORM and WebSocket support
- **Frontend**: Vanilla JavaScript SPA with Tailwind CSS styling
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time**: Flask-SocketIO for live features

### Code Standards
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Maintain comprehensive test coverage
- Document API endpoints and complex logic

### Current Focus Areas
1. **Payment Integration**: Complete Stripe subscription processing
2. **API Integrations**: Connect with review platform APIs
3. **Testing**: Expand test coverage to 80%+
4. **Security**: Implement production security measures

### Development Workflow
- Use feature branches for new development
- Maintain clean commit history
- Update `_meta/TASKS.md` for code changes
- Add ADRs to `_meta/DECISIONS.md` for architectural decisions

## Important Files
- `src/main.py`: Application entry point
- `src/models/`: Database models
- `src/routes/`: API endpoints
- `src/static/`: Frontend assets
- `requirements.txt`: Python dependencies
- `Makefile`: Build and development commands

