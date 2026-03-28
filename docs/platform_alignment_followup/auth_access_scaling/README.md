# Auth And Access Scaling Roadmap

## Purpose

This tracker keeps the auth/access scaling work visible as the product grows from
desktop-first deployment toward a shared desktop + web platform.

The key rule for this block is:

**stabilize one authorization seam before adopting web auth middleware or ABAC adapters.**

## Current Status

Completed in the current slice:

- platform-owned `core/platform/authorization` package with a shared authorization engine seam
- default `SessionAuthorizationEngine` that preserves the current RBAC + scoped-access behavior
- `core/platform/auth/authorization.py` and `core/platform/access/authorization.py` now delegate through the shared engine instead of embedding decision logic directly
- tracker and platform documentation updated so future auth/access work is anchored in-repo
- dedicated `auth_sessions` persistence with per-session issuance, validation, listing, and single-session revocation
- policy-backed separation-of-duties seam instead of a permanently fixed conflict helper
- broader non-project scope rollout with the first platform-owned `site` scope policy and scope-aware site filtering

Still pending:

- web auth transport and middleware
- richer contextual policy inputs for ABAC-like decisions
- broader non-project scope rollout beyond `site` and `storeroom`
- richer configurable enterprise separation-of-duties administration and security workflows

## Execution Order

### 1. Shared Authorization Engine Seam

Status: completed

Scope:

- introduce one shared authorization engine package under `core/platform/authorization`
- keep current session-backed RBAC and scope behavior unchanged
- route existing permission and scope helpers through the engine

Acceptance notes:

- current desktop behavior remains stable
- future policy adapters have one integration point
- auth/access helpers stop growing separate decision logic

Non-goals for this slice:

- no hosted session/token transport yet
- no ABAC library integration yet
- no change to current permission vocabulary yet

### 2. Session Model For Desktop + Web

Status: completed

Scope:

- introduce dedicated session persistence instead of tracking all live-session state only on the user row
- support multiple concurrent device/browser sessions
- add per-session revocation and richer device metadata

Acceptance notes:

- desktop sessions still work
- hosted web can revoke one session without revoking all sessions for the user
- auth middleware can validate concrete session records instead of only user-level expiry state

Non-goals for this slice:

- no OIDC rollout yet
- no refresh-token transport design yet beyond the internal session model

### 3. Web Auth Transport And Federation

Status: planned

Scope:

- add the future ASGI/FastAPI auth middleware layer
- integrate OIDC / hosted SSO adapters on top of the internal auth model
- separate browser/session transport from core business services

Acceptance notes:

- platform auth is consumable by both desktop and web surfaces
- federated sign-in does not bypass core auth/account policy

Non-goals for this slice:

- no ABAC rollout yet
- no replacement of existing desktop login flow

### 4. Contextual Policy Enrichment

Status: planned

Scope:

- extend the authorization engine to accept richer resource/context inputs
- stop treating stored permission snapshots as the long-term policy source of truth
- prepare an adapter seam for a future library such as Oso if ABAC/ReBAC becomes necessary

Acceptance notes:

- policy evaluation can consider subject, action, scope, and resource context in one place
- services do not need bespoke inline policy logic for each new context rule

Non-goals for this slice:

- no immediate third-party policy engine adoption required
- no broad permission-code renaming

### 5. Enterprise SoD And Security Workflows

Status: in progress

Scope:

- move from a fixed conflict list toward configurable separation-of-duties rules
- expand Security admin workflows for password reset, MFA lifecycle, and federated identity operations

Acceptance notes:

- enterprise security operations are managed from the platform layer
- SoD rules are not hardcoded to only two conflicts forever

### 6. Broader Scope Rollout

Status: in progress

Scope:

- expand scope-aware enforcement beyond `project`, `storeroom`, and `site`
- add module-owned scope policies for asset, maintenance-area, and future operational scopes
- keep row filtering and scope enforcement centralized

Acceptance notes:

- more business modules can share one access model without falling back to ad hoc checks

## Recommended Library Posture

- Near term: keep the current platform-owned authorization engine and session-backed behavior.
- Web auth phase: use proven auth/federation tooling in the web transport layer.
- Future ABAC phase: plug a policy library behind the shared engine seam if the business rules truly outgrow scoped RBAC.
