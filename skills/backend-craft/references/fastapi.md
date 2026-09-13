# FastAPI mechanics

Read this when building in Python + FastAPI — the greenfield default named in
`references/stack.md`. These are the stack-specific mechanics behind the language-neutral rules;
in another stack, satisfy the same rules with that stack's idioms.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Shape of the app

- **Layered layout**: `routers/` (thin HTTP), `schemas/` (Pydantic request/response), `models/`
  (ORM), `services/` (business logic), plus `config.py`, `dependencies.py`, `database.py`, and an
  app factory in `main.py`. Routes stay thin — a handler that hashes passwords or writes rows is
  the anti-pattern; it can't be tested or reused without HTTP.
- **App factory + lifespan**: build the app in `create_app()`, own startup/shutdown in a
  `lifespan` context (dispose the engine, close clients) — this is where SKILL.md's graceful
  shutdown lives. Schema changes go through Alembic migrations; `create_all` is dev-only.
- **Config via `pydantic-settings`**: a `Settings(BaseSettings)` loaded once from env — this *is*
  the validate-at-startup rule; a missing `DATABASE_URL` fails at boot, not on first query.

## Pydantic v2 schemas are the response-model allowlist

- Separate input and output models per resource (`UserCreate` / `UserUpdate` / `UserResponse`);
  the response model with `model_config = {"from_attributes": True}` is what makes "never return
  ORM objects" enforceable — declare `response_model=` on **every** route.
- Cross-field rules live in `@model_validator(mode="after")`; update models make every field
  optional and apply with `model_dump(exclude_unset=True)` so PATCH means patch.

## Dependency injection

- Everything a handler needs arrives via `Depends`, aliased once:
  `DbDep = Annotated[AsyncSession, Depends(get_db)]`, `CurrentUserDep = ...` — handlers declare
  `db: DbDep` and tests override one function (`app.dependency_overrides[get_db]`) instead of
  patching internals.
- Split **authentication** (`get_current_user` → `401` + `WWW-Authenticate`) from
  **authorization** (`get_current_active_user`, role checks → `403`) as chained dependencies —
  that's how the 401/403 distinction in `references/api-design.md` stays honest.

## Service layer owns transactions

- Services take the session, do the work, and **let the database enforce uniqueness**: attempt
  the insert, catch `IntegrityError`, rollback, raise a typed domain error (`DuplicateUserError`).
  A `SELECT`-then-`INSERT` precheck is a race; the unique index is the truth — which means the
  index must exist in the model.
- Domain errors are FastAPI-free; routers (or a global `@app.exception_handler`) translate them
  into the one problem+json response.
- **Async all the way down**: async SQLAlchemy, `await db.execute(select(...))` — one sync driver
  call in an async route blocks the event loop for every request. Paginated queries always carry
  `.order_by(...)` on a unique key.

## Testing

- Integration tests drive the real app over ASGI: `httpx.AsyncClient(transport=ASGITransport(app=...))`
  — no live server, real routing, real validation, real problem+json responses.
- Enter the application's lifespan before opening that client and exit it after the client closes;
  HTTPX's ASGITransport does not run startup/shutdown. Use the repository's existing lifecycle
  fixture, or a lifespan manager when none exists, so startup resources and cleanup are exercised.
  Set the client's `base_url` when tests use relative request paths.
  [HTTPX owns this contract](https://www.python-httpx.org/advanced/transports/#asgi-startup-and-shutdown).
- Fixtures compose: fresh schema per test, a session-override `client`, then `registered_user` →
  `auth_token` → `auth_client` so authenticated tests cost one fixture argument. The DB is a real
  ephemeral one per SKILL.md's testing gate — in-memory SQLite only where the SQL stays portable.
