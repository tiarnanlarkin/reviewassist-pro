# ReviewAssist Pro

AI-powered review management platform for businesses to monitor, analyze, and respond to customer reviews across multiple platforms.

## Features

- **Multi-Platform Review Management**: Google, Yelp, Facebook, TripAdvisor integration
- **AI-Powered Response Generation**: Automated, contextual review responses
- **Real-Time Analytics**: Live dashboards and performance metrics
- **Advanced Reporting**: Custom reports with PDF/Excel export
- **Team Collaboration**: Role-based access and workflow management
- **Automation Workflows**: Scheduled tasks and rule-based actions
- **Subscription Management**: Flexible pricing tiers and billing
- **API Integration**: RESTful API with webhook support

## Tech Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Tailwind CSS
- **Database**: SQLite (development), PostgreSQL (production)
- **Real-time**: WebSocket (Flask-SocketIO)
- **AI**: OpenAI GPT API
- **Payments**: Stripe
- **Deployment**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend tooling)
- Redis (for real-time features)
- PostgreSQL (for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/tiarnanlarkin/reviewassist-pro.git
   cd reviewassist-pro
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   make install
   ```

4. **Run development server**
   ```bash
   make dev
   ```

5. **Access the application**
   - Open http://localhost:5000
   - Demo credentials: admin@reviewassist.com / Admin123!

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Project Structure

```
reviewassist-pro/
├── src/
│   ├── models/          # Database models
│   ├── routes/          # API endpoints
│   ├── static/          # Frontend assets
│   ├── database/        # Database files
│   ├── main.py          # Application entry point
│   └── scheduler.py     # Background tasks
├── tests/               # Test suite
├── docs/                # Documentation
├── scripts/             # Utility scripts
├── .github/workflows/   # CI/CD pipelines
├── requirements.txt     # Python dependencies
├── requirements-dev.txt # Development dependencies
├── Dockerfile          # Container configuration
├── docker-compose.yml  # Multi-service setup
└── Makefile           # Build automation
```

## Development

### Available Commands

```bash
make help          # Show available commands
make install       # Install dependencies
make dev           # Run development server
make test          # Run test suite
make lint          # Run code linting
make format        # Format code
make clean         # Clean build artifacts
make build         # Build for production
make deploy        # Deploy to production
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type checking
mypy src/
```

## API Documentation

The API provides comprehensive endpoints for:

- **Authentication**: `/api/auth/*`
- **Reviews**: `/api/reviews/*`
- **Analytics**: `/api/analytics/*`
- **Subscriptions**: `/api/subscription/*`
- **Integrations**: `/api/integrations/*`
- **Real-time**: WebSocket events

### Example API Usage

```python
import requests

# Get reviews
response = requests.get('http://localhost:5000/api/reviews', 
                       headers={'Authorization': 'Bearer <token>'})

# Create review response
response = requests.post('http://localhost:5000/api/reviews/1/respond',
                        json={'response_text': 'Thank you for your feedback!'},
                        headers={'Authorization': 'Bearer <token>'})
```

## Deployment

### Environment Variables

Key environment variables (see `.env.example`):

- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection for real-time features
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `STRIPE_SECRET_KEY`: Stripe secret key for payments
- `SECRET_KEY`: Flask secret key

### Production Deployment

1. **Configure environment variables**
2. **Set up database** (PostgreSQL recommended)
3. **Configure Redis** for real-time features
4. **Set up reverse proxy** (Nginx recommended)
5. **Configure SSL certificates**
6. **Deploy using Docker** or platform-specific method

### Hosting Platforms

- **Manus**: Direct deployment support
- **DigitalOcean**: App Platform or Droplets
- **AWS**: ECS, Elastic Beanstalk, or EC2
- **Google Cloud**: Cloud Run or Compute Engine
- **Heroku**: Git-based deployment

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Use conventional commit messages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/tiarnanlarkin/reviewassist-pro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tiarnanlarkin/reviewassist-pro/discussions)

## Roadmap

- [ ] Mobile application (React Native)
- [ ] Advanced AI features (sentiment analysis, trend prediction)
- [ ] Enterprise SSO integration
- [ ] White-label solutions
- [ ] Advanced workflow automation
- [ ] Multi-language support

