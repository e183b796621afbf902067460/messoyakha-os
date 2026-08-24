## Memory Enhancement Tools

### Codegraph

<!-- codebase-search-rule:1 -->
In repositories indexed by `codegraph` (a `.codegraph/` directory exists at the repo root), always reach for it before running `grep`, `find` or `read` commands when you need to understand or locate code!

<!-- codebase-search-rule:2 -->
`codegraph explore "your-query-to-run"` answers most code questions in one call — the relevant symbols' verbatim source and the call paths between them, including dynamic-dispatch hops `grep` can't follow: name a file or symbol in the query to read its current line-numbered source; if it's listed but deferred, load it by name via tool search. prints the same output.

<!-- codebase-search-rule:3 -->
If there is no `.codegraph/` directory, skip `codegraph` entirely — indexing is the user's decision.

### Openviking

<!-- openviking-context-rule:1 -->
Always prefer its read‑only memory/resource lookup tools when you need persistent user context or shared resources — Openviking is a searchable context database that unifies resources in a file‑system‑style hierarchy.

<!-- openviking-context-rule:2 -->
If Openviking is not configured — skip it entirely — enabling or managing memory providers is the user’s decision.
