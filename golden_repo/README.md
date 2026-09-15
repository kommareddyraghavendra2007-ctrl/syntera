# ShopCore — E-Commerce Backend

ShopCore is a production-grade e-commerce backend built with Python and FastAPI.
It handles user accounts, JWT authentication, product catalog, and order management.

## Architecture

```
src/
  auth/         — JWT authentication, token management, password hashing
  users/        — User registration, profile management, UserRepository
  orders/       — Order lifecycle: create, confirm, ship, cancel
  database/     — SQLAlchemy models, session management, base ORM
  api/          — FastAPI route handlers (thin controllers)
  config/       — Application configuration, environment variables
tests/          — Unit tests for all modules
```

## Tech Stack

- **Framework**: FastAPI
- **Auth**: JWT (PyJWT) + bcrypt password hashing
- **Database**: PostgreSQL via SQLAlchemy ORM (SQLite for development)
- **Cache**: Redis for session data

## Environment Variables

```
DATABASE_URL=postgresql://user:password@localhost:5432/shopcore
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=60
JWT_REFRESH_EXPIRY_DAYS=30
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
APP_ENV=development
DEBUG=true
```

## Quick Start

```bash
pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /auth/register | Register a new user |
| POST | /auth/login | Authenticate and receive JWT |
| POST | /auth/logout | Revoke refresh token |
| POST | /auth/refresh | Refresh access token |
| GET | /users/me | Get current user profile |
| PUT | /users/me | Update profile |
| GET | /orders | List user orders |
| POST | /orders | Create a new order |
| GET | /orders/{id} | Get order details |
| POST | /orders/{id}/cancel | Cancel an order |
