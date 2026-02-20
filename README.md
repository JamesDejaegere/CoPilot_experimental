# MSC Digital Solutions MVP Prototype

Working prototype for a focused subset of requirements from `MSC_Digital_Solutions_Requirements.docx`.

## MVP Scope

This implementation delivers a functional demo for key user stories:

- Shipment tracking by container number, B/L number, or booking number.
- Event milestone timeline with status and ETA.
- Notification preferences (email/push) with role-based access control.
- Lightweight backend API with session-based auth and persisted notification settings.

## Run the Application

Start the backend (which also serves the frontend):

```bash
python server.py
```

Then open:

```text
http://localhost:8000
```

If port `8000` is already in use:

```bash
PORT=8001 python server.py
```

### Troubleshooting: login returns 501

If you see `501 Unsupported method ('POST')`, you likely started a static server (`python -m http.server`) instead of the backend server.

- Stop the static server.
- Start this app with `python server.py` (or `PORT=8001 python server.py`).
- Open the same port in the browser as the backend server.

## Demo Login

- Email: any valid email
- Password: `demo`
- Roles:
  - `shipper`
  - `freight_forwarder`
  - `viewer`
  - `admin`

## What Is Implemented

- Role-aware login with backend session cookie.
- Tracking search by `container`, `bl`, and `booking` reference.
- Shipment detail cards + chronological milestone event log.
- Notification preferences persisted in `data/notification_prefs.json`.
- Role restriction: `viewer` can track but cannot save notification preferences.
- Audit log records written to `data/audit.log` (JSON lines).
- Input validation for email format, search reference format, and notification booleans.

## Out of Scope

- External enterprise integrations (INTTRA, GT Nexus, CargoSmart).
- Full production identity stack (OAuth/OIDC/MFA/SSO).
- eBL issuance/endorsement workflows.
- IoT ingest pipelines for smart container and reefer telemetry.

## Demo API Endpoints

- `GET /api/health`
- `POST /api/login` (`email`, `password`, `role`)
- `POST /api/logout`
- `GET /api/me`
- `GET /api/shipments/search?type=container|bl|booking&value=...`
- `GET /api/notifications`
- `PUT /api/notifications` (`email`, `push`)

## Request Tracing

- Every API response includes header `X-Request-ID`.
- Every JSON API response includes `requestId`.
- Audit records in `data/audit.log` include the same `requestId` for correlation.

## Error Response Model

API errors now follow this shape:

```json
{
  "error": {
    "code": "INVALID_JSON",
    "message": "Request body must be valid JSON."
  },
  "requestId": "..."
}
```

Current error codes:

- `NOT_FOUND`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `INVALID_JSON`
- `INVALID_LOGIN_PAYLOAD`
- `INVALID_CREDENTIALS`
- `INVALID_SEARCH_PARAMS`
- `INVALID_SEARCH_FORMAT`
- `INVALID_NOTIFICATION_PAYLOAD`

## Validation Rules

- `POST /api/login`: valid email format, supported role, password must be `demo`.
- `GET /api/shipments/search`: `type` must be `container|bl|booking`; `value` must match expected format.
- `PUT /api/notifications`: `email` and `push` must be booleans.

## Audit Log

- File: `data/audit.log`
- Format: one JSON record per line
- Captures: timestamp, action, endpoint, status, success, client IP, and user context

## Requirements Traceability

| Requirement ID | Description | Status | Implementation Note |
|---|---|---|---|
| FR-01 | User Registration & Login | Partial | Login is implemented, registration and external IdP are not |
| FR-02 | Role-Based Access Control | Built (MVP) | Role permissions enforced for notification actions |
| FR-09 | Shipment Tracking by Container # | Built (MVP) | Search type `container` |
| FR-10 | Shipment Tracking by B/L or Booking # | Built (MVP) | Search types `bl` and `booking` |
| FR-11 | Event Milestone Log | Built (MVP) | Event timeline shown per shipment |
| FR-12 | Automated Tracking Notifications | Built (MVP, simplified) | User can save email/push preferences |
| FR-26 | REST API for Tracking Data | Partial | Internal demo API for tracking and preferences |
| NFR-02 | Performance | Partial | Lightweight app, no formal load/perf testing |
| NFR-03 | Security | Partial | Session cookie + prototype auth, not production-grade |

## AI Usage Log

- Tooling: GitHub Copilot agent (model: GPT-5.3-Codex).
- AI-assisted tasks:
  - Requirements extraction and scoping.
  - Frontend and backend implementation.
  - Traceability matrix and demo documentation.
- Validation:
  - API flow checks for login/search/notification persistence.
  - Edge case behavior for unknown tracking references.
- Reflection:
  - Strong acceleration for scaffolding and integration.
  - Production security and external integrations remain future work.

## 5-Minute Demo Script

1. Start server and open the app.
2. Login as `viewer`; show tracking works and notification save is blocked.
3. Search `MSCU1234567`; show status and milestone timeline.
4. Search an unknown reference; show empty/not-found behavior.
5. Logout and login as `shipper`; save notification preferences.
6. Close with the traceability table and explicitly call out mocked/partial areas.
