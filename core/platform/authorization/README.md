# Platform Authorization Engine

This package owns the shared authorization decision seam for the application.

## Purpose

It centralizes:

- global permission checks
- scope-aware permission checks
- row filtering for restricted scope access
- the future adapter seam for richer contextual policy evaluation

## Current Implementation

The current default engine is session-backed:

- `SessionAuthorizationEngine`
- `get_authorization_engine()`
- `set_authorization_engine()`

Today it preserves the existing behavior by delegating to `UserSessionContext`.

That keeps desktop behavior stable while creating one place where future web/API
policy middleware or ABAC-style evaluation can plug in.

## Near-Term Goal

Short term, this engine remains RBAC + scoped-access aware.

Later, this seam is where:

- per-request web authorization context
- resource attributes
- tenant/module-aware policy adapters
- ABAC or relationship-based checks

should be introduced without rewriting every service callsite again.
