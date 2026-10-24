# GitPulse Database Migrations (Alembic / PostgreSQL)

This directory manages database schema versioning and Alembic migrations.

## Applying Migrations
```bash
alembic upgrade head
```

## Reverting Migrations
```bash
alembic downgrade -1
```

## Generating New Migration
```bash
alembic revision --autogenerate -m "add_table_name"
```
