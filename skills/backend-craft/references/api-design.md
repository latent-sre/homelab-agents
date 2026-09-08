# API surface design

Read this when shaping the HTTP surface itself — new endpoints, resource naming, status codes,
list-endpoint query conventions, or evolving a published API. The core rules (contract-first, one
error shape, `/v1`, paginate-by-default) say *that* these exist; this file is *how* they look.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Resources and methods

- **URLs are plural kebab-case nouns**; ownership nests one level (`/v1/users/123/orders`). Verbs
  only for actions that genuinely aren't CRUD (`POST /v1/orders/123/cancel`) — a verb elsewhere
  (`/getUsers`) is a smell.
- Method semantics are a contract: GET is safe and idempotent; PUT replaces the representation
  idempotently; DELETE is idempotent in intended effect, even when repeated responses differ.
  POST and PATCH are not guaranteed idempotent. A PATCH that sets a field can be idempotent;
  one that increments or appends can repeat its effect. Define retry behavior per operation,
  using server-supported idempotency keys or conditional requests such as ETag/If-Match where
  appropriate. After a lost response, reconcile an unknown outcome rather than blindly replaying
  a mutation. [RFC 5789 section 2](https://www.rfc-editor.org/rfc/rfc5789#section-2) owns PATCH semantics.

## Status codes carry meaning — don't flatten them

- `200` read/update with body · `201` create **with `Location` header** · `204` no body
  (DELETE, some PUTs).
- Client errors, precisely: `400` malformed (bad JSON), `422` well-formed but semantically invalid
  (field details in the problem+json `errors` extension member), `401` not authenticated, `403`
  authenticated but not allowed, `404` no such resource, `409` state conflict (duplicate, version
  mismatch), `429` rate limited **with `Retry-After`**.
- Never `200 {"success": false}` — clients branch on status codes, not body flags. Never `500`
  for a validation failure; a 5xx means *the server* broke.

## List-endpoint query conventions

Pick these once and hold them across every endpoint — consistency is the feature:

- **Filtering**: query params, equality by default (`?status=active`), bracket operators for
  ranges (`?price[gte]=10`), comma for multi-value (`?category=a,b`).
- **Sorting**: `?sort=-created_at,name` — leading `-` for descending, comma for tiebreakers.
  Always sort on a unique final key (append `id`) or pagination skips and repeats rows.
- **Cursor pagination mechanics**: fetch `limit + 1` rows to learn `has_next` without a count
  query; the cursor is opaque to the client (encode the sort-key values, not an offset). Cap
  `limit` server-side. Offset pagination is acceptable only where SKILL.md allows it (small,
  bounded admin lists) — it degrades at depth and shifts under concurrent writes.

## Typed errors feed the one problem+json response

- Raise a **typed error hierarchy** in the domain layer — a base app error carrying `code` +
  HTTP status, subclasses per case (`NotFound`, `Conflict`, `Validation` with field details) —
  and translate to the SKILL.md problem+json shape in **one global exception handler**, not per
  route.
- The unexpected-exception path is part of the design: log the full error with the request ID,
  return a generic `internal_error` problem response. Internals (stack traces, SQL, upstream bodies)
  never reach the client.
- Error codes are API contract: enumerate them in the OpenAPI spec, and treat renaming one as a
  breaking change.

## Evolving a published surface

A surface is **published** when a consumer you cannot coordinate with builds on it. An API whose
only consumer deploys atomically with it — the operator's own frontend, shipped by the same commit
and the same deploy — is not published: change both sides at once, and use the breaking-change
taxonomy below to notice what *would* break, not to run a versioning protocol. One caveat even
then: an already-loaded client (yesterday's bundle in an open tab) is a consumer you cannot
coordinate with — acceptable when the break heals on reload, published-surface rules when it would
corrupt data. Everything in this section earns its cost from the first consumer you cannot reach.

- **Everything observable becomes a dependency** (Hyrum's Law) — undocumented field order, error
  message text, quirks included. Expose deliberately; what clients can see, they will build on.
- **Extend, don't mutate**: new fields optional, new params optional, new endpoints freely.
  Removing or renaming a field, changing a type, or changing auth is a breaking change — that's
  what a new `/v2` is for, and you run at most two versions at once.
- **Deprecation is a protocol, not a deletion**: announce, add a `Sunset` header with the date,
  return `410 Gone` after it. Silent removal is an outage you scheduled for someone else.
- **Gate the contract in CI**: diff every spec change with a breaking-change detector (oasdiff or
  equivalent) so a removal, rename, type change, or new-required-field cannot merge unlabeled —
  the taxonomy above, enforced mechanically.
