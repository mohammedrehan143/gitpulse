# GitPulse API Specifications & OpenAPI Schema

## Base URL
- Production: `https://api.gitpulse.internal/api/v1`
- Local Development: `http://localhost:8000/api/v1`

## Authentication
- Header: `Authorization: Bearer <JWT_OR_API_KEY>` (production)

## Endpoints

### 1. `GET /health`
Returns service uptime and operational status.
- **Response**: `200 OK`
```json
{
  "status": "HEALTHY",
  "version": "0.1.0",
  "environment": "development"
}
```

### 2. `GET /repos/{owner}/{repo}/velocity`
Retrieves developer velocity summary and daily timeline metrics.
- **Parameters**:
  - `timeframe`: string (`7d`, `14d`, `30d`, `90d`, `1y`)
  - `granularity`: string (`hour`, `day`, `week`)
- **Response**: `200 OK`

### 3. `GET /repos/{owner}/{repo}/events`
Paginated GitHub activity event feed.
- **Parameters**:
  - `limit`: integer (1-100)
  - `offset`: integer (>= 0)
- **Response**: `200 OK`

### 4. `POST /webhooks/github`
Inbound webhook intake with `X-Hub-Signature-256` HMAC validation.
- **Response**: `202 Accepted`
