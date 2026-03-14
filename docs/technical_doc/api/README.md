# API Transport Layer

`api/` contains transport-facing adapters for future remote delivery.

## Current Scope

The current implementation is a lightweight HTTP-style transport seam:

- `http/platform/models.py`
- `http/platform/runtime.py`

## What It Does

The transport adapter provides:

- request DTOs
- response DTOs
- JSON-ready payloads
- HTTP-like status codes
- normalized error payloads for domain exceptions

It delegates all real behavior to `application/platform/runtime/service.py`.

## What It Does Not Do Yet

- no FastAPI router
- no ASGI app
- no hosted server process
- no auth middleware

That work is intentionally deferred until the product actually moves to a web deployment.

## Design Rule

- transport adapters must not reimplement business rules
- concrete server/router code should wrap this layer, not bypass it
