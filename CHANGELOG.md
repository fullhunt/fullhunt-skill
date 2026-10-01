# Changelog

## 2.1.1 (2026-09-30)
Fixes from an independent review against the live API (2026-09-30).
- Advisory and feed `package` filters take `ecosystem/name` (`npm/lodash`).
- Global search results are raw host documents, not the host object; MCP `global_search` exposes 47 of the 49 REST filters.
- POST vuln/exploit/advisory search reads form fields only; CVE IDs are case-sensitive (uppercase).
- OEM scan status: `scan_completed` is the only terminal status (no `in_progress`/`failed`); polling loop fixed.
- Enterprise `org` parameter is an organization id; alert fields corrected; org delete lists everything it removes.
- Nexus: whois/search ANDs `tld`; the HTTP-200-with-error cases are listed exactly and are charged.
- `auth_status` returns no plan name; README check uses `user_credits`.
- Added: OEM accounts pay standard routes from the OEM pool, 24h scan dedup, 413 and non-JSON error bodies, global-search silent no-ops, domain 404s that are charged, MCP result/error wrapping, `oem_darkweb_search` has no date filter, feed vs MCP plan gates.
- Trigger keywords no longer fire on generic "mcp" / "agentic ai".

## 2.1.0 (2026-09-30)
Verified against the live API and the MCP server (65 tools).
- Org DB, vulnerability, exploit and advisory search deduct one credit (API change 2026-09-30).
- Enterprise module gates now enforced by the API: Data Intelligence on `/intel/*`, Global Search (flag, filter allow-list, own credit pool, vulnerability access), dark-web module on compromised-credentials.
- Enterprise on-demand scans charge 1 credit per new scan (24h repeats free) and return `scan_id`/`deduplicated`; 503 when submission is disabled.

## 2.0.0 (2026-09-28)

Re-verified every route against the FullHunt API and its OpenAPI specification (63 operations).

### Added
- Endpoints: vulnerability intelligence feed, advisories search (standard and OEM), Nexus WHOIS lookup/search, OEM WHOIS lookup/search, OEM vulnerabilities/alerts/historical-hosts search, OEM feed, and the eight enterprise organization/asset management routes (with safety rules).
- Access-tier table rebuilt from the API's auth decorators, per-route credit and rate-limit columns, tier result caps.
- "Known API quirks" section (nexus 200-with-error bodies, intel not paginated, `resolvable_only` ignored, whois OR vs AND, alerts without totals, default 100/hour limit on six OEM routes).
- Per-family response shapes and error body formats; per-route page sizes.
- Full MCP tool reference with parameters; Claude Code, Cursor (`~/.cursor/mcp.json`) and Claude Desktop (`mcp-remote`) setup.
- `scripts/check_drift.py`: fails if the skill's routes or MCP tools drift from the OpenAPI spec and the MCP tool list.
- `metadata.version` in SKILL.md frontmatter.
- OEM dark web search `from`/`to` date-added filter (added to the API 2026-09-28).

### Fixed
- Global search is available to any key with credits (was "enterprise only"); documented all 49 filters, aliases, `page`/`limit` (≤200) and response fields.
- `/attack-surface/on-demand-scan` requires an enterprise account (was "public").
- Vuln-search `query` is 3–100 chars (was 3–50); OEM vuln search no longer claims fields it does not return.
- Enterprise discovered-emails uses `q` (was `query`); OEM on-demand scan `type` includes `host`; OEM audit logs have a fixed 50/page (no `per_page`).
- Host object field names match the API (`subject_common_name`, `issuer_common_name`, `ip_metadata.country_name`, ...); removed `asset_score` from enterprise assets (not returned).
- Removed the uniform `{status, message, metadata}` envelope claim and the `X-RateLimit-*` / `retry_after` claims (not sent).
- Credits: no data route is described as free.
- MCP: removed nonexistent tools `get_my_ip` and `oem_vulnerability_intelligence`; fixed parameter names; removed the duplicate row; paid-plan and Bearer-auth notes.
- README: Claude Code install, MCP section, coverage table.

## 1.0.0 (2026-03-06)
- Initial release.
