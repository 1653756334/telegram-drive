# Telegram Drive Backend v2.0

A modern, well-architected file storage system using Telegram as the backend storage provider.

## 🏗️ Architecture

This project follows **Domain-Driven Design (DDD)** principles with a **Clean Architecture** approach:

```
app/
├── config/           # Configuration layer
├── core/             # Core utilities (security, exceptions, dependencies)
├── domain/           # Business logic layer
│   ├── entities/     # Domain entities (User, Node, Channel)
│   ├── repositories/ # Repository interfaces
│   └── services/     # Domain services
├── application/      # Application layer
│   ├── schemas/      # Pydantic models for API
│   └── use_cases/    # Application use cases
├── infrastructure/   # Infrastructure layer
│   ├── database/     # Database models and repositories
│   └── telegram/     # Telegram client integration
└── presentation/     # Presentation layer
    ├── api/          # REST API routes
    └── middleware/   # HTTP middleware
```

## 🎯 Key Principles

### High Cohesion, Low Coupling
- **Domain Layer**: Contains pure business logic, no external dependencies
- **Application Layer**: Orchestrates use cases, depends only on domain
- **Infrastructure Layer**: Implements external concerns (database, Telegram)
- **Presentation Layer**: HTTP API, depends on application layer

### Dependency Inversion
- High-level modules don't depend on low-level modules
- Both depend on abstractions (interfaces)
- Repository pattern abstracts data access

### Single Responsibility
- Each class/module has one reason to change
- Clear separation of concerns across layers

## 🚀 Features

### Core Functionality
- **File Management**: Upload, download, move, rename, delete files
- **Directory Structure**: Hierarchical folder organization
- **Deduplication**: Automatic file deduplication by checksum
- **Soft Delete**: Recycle bin functionality
- **Large File Support**: Handles files up to 2GB via user client

### Technical Features
- **Modern Python**: Type hints, async/await, Pydantic v2
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **API**: FastAPI with automatic OpenAPI documentation
- **Security**: Encrypted session storage, optional API tokens
- **Error Handling**: Comprehensive exception hierarchy
- **Logging**: Structured logging with context

## 📦 Installation

1. **Clone and setup**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run migrations**:
```bash
alembic upgrade head
```

4. **Start server**:
```bash
python run.py
# or
uvicorn app.main:app --reload
```

## 🔧 Configuration

Environment variables (prefix: `TGDRIVE_`):

```env
# Telegram API
TGDRIVE_API_ID=your_api_id
TGDRIVE_API_HASH=your_api_hash
TGDRIVE_BOT_TOKEN=your_bot_token

# Security
TGDRIVE_SESSION_SECRET=your_secret_key
TGDRIVE_API_TOKEN=optional_api_token

# Database
TGDRIVE_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Storage
TGDRIVE_STORAGE_CHANNEL_USERNAME=@your_channel
# OR
TGDRIVE_STORAGE_CHANNEL_ID=-100xxxxxxxxx

# Application
TGDRIVE_DEBUG=false
TGDRIVE_CORS_ORIGINS=["*"]
```

## 📚 API Documentation

When running in debug mode, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/send-code` - Send login verification code
- `POST /api/v1/auth/verify-code` - Verify code and login
- `GET /api/v1/auth/me` - Get current user info

#### Files
- `GET /api/v1/files/` - List directory contents
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files/id/{file_id}/download` - Download file
- `POST /api/v1/files/id/{file_id}/move` - Move/rename file
- `DELETE /api/v1/files/id/{file_id}` - Delete file

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app_new

# Run specific test
pytest tests/test_domain/test_entities.py
```

## 🔄 Migration from v1.0

The new architecture is designed to be backward compatible. To migrate:

1. **Database**: Existing database schema is compatible
2. **API**: Endpoints remain the same, responses may have additional fields
3. **Configuration**: Same environment variables

## 🛠️ Development

### Adding New Features

1. **Domain First**: Define entities and repository interfaces
2. **Use Cases**: Implement business logic in application layer
3. **Infrastructure**: Implement repository and external integrations
4. **API**: Add presentation layer endpoints
5. **Tests**: Write comprehensive tests for each layer

### Code Style

- **Type Hints**: All functions must have type annotations
- **Docstrings**: All public methods need docstrings
- **Error Handling**: Use custom exceptions, not generic ones
- **Async/Await**: Prefer async patterns for I/O operations

## 📈 Performance

- **Connection Pooling**: SQLAlchemy async engine with connection pooling
- **Lazy Loading**: Efficient database queries with proper relationships
- **Caching**: Settings cached with `@lru_cache`
- **Streaming**: Large file downloads use streaming responses

## 🔒 Security

- **Session Encryption**: All Telegram sessions encrypted at rest
- **API Authentication**: Optional token-based API access
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection**: SQLAlchemy ORM prevents SQL injection
- **CORS**: Configurable CORS origins

## 📊 Monitoring

- **Health Check**: `/health` endpoint for monitoring
- **Structured Logging**: JSON logs with request context
- **Error Tracking**: Comprehensive exception handling
- **Metrics**: Ready for Prometheus integration

## 🤝 Contributing

1. Follow the established architecture patterns
2. Write tests for new functionality
3. Update documentation for API changes
4. Use conventional commit messages

