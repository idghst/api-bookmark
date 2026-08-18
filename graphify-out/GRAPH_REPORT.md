# Graph Report - api-bookmark  (2026-08-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 396 nodes · 1129 edges · 20 communities (16 shown, 4 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `114bee92`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 9
- Community 11
- Community 12
- Community 13
- Community 18

## God Nodes (most connected - your core abstractions)
1. `Settings` - 56 edges
2. `AuthContext` - 40 edges
3. `FakeSupabase` - 35 edges
4. `_client()` - 33 edges
5. `Mutation` - 31 edges
6. `ApiError` - 29 edges
7. `GraphQLContext` - 23 edges
8. `create_app()` - 22 edges
9. `execute()` - 21 edges
10. `resolve()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_verified_access_token_reaches_auth_me()` --uses--> `Settings`  [INFERRED]
  tests/integration/test_supabase.py → app/core/config.py
- `settings()` --uses--> `Settings`  [INFERRED]
  tests/test_auth.py → app/core/config.py
- `test_admin_client_requires_secret_key()` --uses--> `Settings`  [INFERRED]
  tests/test_auth.py → app/core/config.py
- `test_admin_client_uses_only_secret_key_and_closes_client()` --uses--> `Settings`  [INFERRED]
  tests/test_auth.py → app/core/config.py
- `test_auth_context_maps_authentication_failures()` --uses--> `Settings`  [INFERRED]
  tests/test_auth.py → app/core/config.py

## Import Cycles
- None detected.

## Communities (20 total, 4 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (45): create_app(), _assert_user_scoped(), _client(), FakeHttpClient, FakeQuery, FakeResponse, FakeSupabase, Any (+37 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (44): AnyHttpUrl, legacy_health(), liveness(), probe_supabase(), Depends, get, readiness(), clear_settings_cache() (+36 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (77): create_bookmark(), delete_bookmark(), list_bookmarks(), AuthDependency, delete, get, patch, post (+69 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (26): get_graphql_context(), GraphQLContext, Depends, positions(), resolve(), update_values(), BookmarkCreateInput, BookmarkUpdateInput (+18 more)

### Community 4 - "Community 4"
Cohesion: 0.67
Nodes (3): _error_response(), Request, JSONResponse

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (38): alias, me(), Depends, get, get_settings(), get_admin_client(), get_auth_context(), get_resource_auth_context() (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (31): FastAPI, Register public error envelopes without exposing internal details., register_exception_handlers(), configure_logging(), JsonFormatter, JSON logging configuration., Serialize the request fields used by application logs., Configure the root logger with one UTC JSON stream handler. (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.22
Nodes (10): credentials(), IntegrationCredentials, load_integration_credentials(), fixture, MonkeyPatch, parametrize, test_auth_health_endpoint(), test_data_api_accepts_bookmark_schema_profile() (+2 more)

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (6): maxDuration, fluid, framework, functions, app/main.py, $schema

## Knowledge Gaps
- **5 isolated node(s):** `fastapi-bookmark`, `maxDuration`, `fluid`, `framework`, `$schema`
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `Community 1` to `Community 0`, `Community 2`, `Community 5`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._
- **Why does `AuthContext` connect `Community 2` to `Community 0`, `Community 3`, `Community 5`?**
  _High betweenness centrality (0.166) - this node is a cross-community bridge._
- **Why does `ApiError` connect `Community 2` to `Community 1`, `Community 3`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `Settings` (e.g. with `probe_supabase()` and `get_admin_client()`) actually correct?**
  _`Settings` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AuthContext` (e.g. with `me()` and `get_graphql_context()`) actually correct?**
  _`AuthContext` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Mutation` (e.g. with `GraphQLContext` and `BookmarkCreateInput`) actually correct?**
  _`Mutation` has 17 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fastapi-bookmark`, `maxDuration`, `fluid` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._