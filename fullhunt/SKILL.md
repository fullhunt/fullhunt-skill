---
name: fullhunt
description: Interact with the FullHunt attack surface intelligence API (REST via curl + jq, or the hosted MCP server). Use when the user asks to query domains, subdomains, hosts, IP addresses, ASNs, WHOIS, CVEs, vulnerabilities, exploits, security advisories (GHSA/OSV), the vulnerability intelligence feed, dark web exposure, certificates, enterprise alerts or assets, organizations, on-demand scans, global search, OEM APIs, the FullHunt MCP server, or any FullHunt API capability. Requires FULLHUNT_API_KEY. Triggers on "fullhunt", "find subdomains", "host lookup", "whois", "check tor ip", "passive dns", "search CVE", "exploits for", "GHSA", "vuln feed", "dark web", "enterprise alerts", "attack surface scan", "global search", "organizations db", "OEM API", "FullHunt MCP".
metadata:
  version: 2.1.1
  api_version: v1
  verified_against: FullHunt API v1 (2026-09-30)
---

# FullHunt Skill

Query the FullHunt attack surface intelligence platform via REST (`curl` + `jq`) or the hosted MCP server.

## Setup

```bash
export FH_API="${FULLHUNT_BASE_URL:-https://fullhunt.io/api/v1}"
H=(-H "X-API-KEY: $FULLHUNT_API_KEY")
curl -s "$FH_API/auth/status" "${H[@]}" | jq .
```

Call `auth/status` first. It is an account call (no credit) and returns `user` (`email`, `company`, `first_name`, `last_name`) and `user_credits` (`remaining_credits`, `total_credits_per_month`, `credits_usage`, `max_results_per_request`). The plan name is not returned; infer the tier from `max_results_per_request` (100 visitor, 500 free, 100000 paid) and let 403s tell you about enterprise/OEM gates.

**Base URLs** (same routes on both):
- `https://fullhunt.io/api/v1`
- `https://enterprise-api.fullhunt.io/api/v1` (recommended for enterprise and OEM accounts)
- MCP: `<base>/mcp` (paid plans or enterprise). See `references/agentic-ai.md`.

**Auth:** REST routes accept only the `X-API-KEY` header. The MCP endpoint also accepts `Authorization: Bearer <key>`.

## Access tiers (enforced by the API)

| Gate | Routes |
|---|---|
| None | `GET /public/my-ip` |
| Any valid key | domain, host, intel, nexus, org DB search, vuln/exploit/advisory search, global search, `auth/status` |
| Enterprise keys only: module gates on shared routes | `/intel/*` needs the Data Intelligence module; `POST /global/search` needs the Global Search module (plus its filter allow-list and its own credit pool) |
| Paid plan (builder, scale, professional, consultant, enterprise) or OEM | `GET /vulnerability-intelligence/feed` (checks the user's own plan; an enterprise-linked user on a non-paid plan gets 403) |
| Paid plan or any active enterprise account | MCP |
| Enterprise account (active; expired trials get 403) | `/enterprise/*`, `GET /attack-surface/on-demand-scan` |
| Enterprise + dark-web module | all four `/enterprise/darkweb/*` routes |
| Enterprise + OEM module | `/oem/*` |

On 403, read the `message`/`error` text. It names the missing entitlement (credits, paid plan, OEM, dark-web module). Do not retry a 403.

## Credits: every data call costs

FullHunt has no free data APIs. Budget one credit per request (not per result) before loops or fan-outs.
- **Standard credits:** domain, host, intel, nexus, global search, vulnerability/exploit/advisory search, org DB search, vuln feed, on-demand scans.
- **OEM accounts** pay every one of those from the OEM credit pool too, as well as every `/oem/*` data route (charged on 2xx, including cache hits).
- **Not charged:** account and meta calls (`auth/status`, `public/my-ip`, `oem/account/credits`, `oem/account/audit-logs`, `oem/on-demand-scan/scan-status`), and a repeat scan of the same target within 24h.
- **Enterprise:** `/enterprise/*` reads are covered by the subscription; enterprise on-demand scans cost 1 credit; global search uses the Global Search module's credits. An enterprise account whose enrollment is incomplete has 0 credits.

Results per request are capped by tier: visitor 100, free 500, paid 100,000. Compare `metadata.all_results_count` with `metadata.available_results_for_user` to detect truncation.

## Quick reference

Full parameters, limits and response shapes are in `references/endpoints.md`.

| Task | Endpoint | Rate |
|---|---|---|
| Account, plan, credits | `GET /auth/status` | 60/min |
| My IP (no auth) | `GET /public/my-ip` | 60/min |
| Domain hosts (full objects) | `GET /domain/{domain}/details` | 200/hour |
| Subdomain names only | `GET /domain/{domain}/subdomains` | 200/hour |
| Host | `GET /host/{host}` | 10/min |
| On-demand scan (enterprise) | `GET /attack-surface/on-demand-scan?target=` | 10/min |
| Org DB search | `GET /organizations-db/search?query=` | 60/min |
| CVE search | `GET /vulnerability-intelligence/vulnerability-search?query=` | 60/min |
| Exploit search | `GET /vulnerability-intelligence/exploits-search?query=` | 60/min |
| Advisory search (GHSA, OSV, PYSEC…) | `GET /vulnerability-intelligence/advisories-search?query=&ecosystem=&package=` | 60/min |
| Vuln intel feed (paid) | `GET /vulnerability-intelligence/feed?days=&type=&keywords=` | 30/min |
| Global search | `POST /global/search` | 60/min |
| Intel lookups (11) | `GET /intel/{host,tag,web-tech,product,domain,ip-to-hosts,asn-to-hosts,asn-to-virtual-hosts,ip-range-to-hosts,dns-mx-to-hosts,dns-ns-to-hosts}` | 60/min |
| IP or host enrichment | `GET /nexus/ip-lookup?query=` | 60/min |
| Tor exit check | `GET /nexus/tor/check-ip?ip=` | 60/min |
| Cloud cert DNS search | `GET /nexus/cloud-certs/dns-search?query=` | 60/min |
| Passive DNS | `GET /nexus/passive-dns/lookup?domain=` | 60/min |
| Domain to company profile | `GET /nexus/domain-collection/lookup?domain=` | 60/min |
| Company to domains | `GET /nexus/domain-collection/company-lookup?query=` | 60/min |
| WHOIS lookup | `GET /nexus/whois/lookup?domain=` | 60/min |
| WHOIS search | `GET /nexus/whois/search?registrar=&nameserver=&tld=&status=&expires_before=&limit=` | 30/min |
| Enterprise reads | `GET /enterprise/{organizations,alerts,vulnerabilities,entities,assets,certificates,suggested-domains}` | 20–60/min |
| Enterprise scan (active, 1 credit) | `GET /enterprise/on-demand-scans?target=` | 10/min |
| Enterprise dark web | `GET /enterprise/darkweb/{compromised-credentials,discovered-emails,potential-phishing,typosquatting}` | 60/min |
| Enterprise management (writes) | `POST/DELETE /enterprise/organizations…`, `…/domains`, `…/ip-ranges`, `PUT …/settings` | 10–20/min |
| OEM (all POST JSON) | `/oem/attack-surface/{search,host}`, `/oem/{organizations,darkweb,vulnerabilities,alerts,historical-hosts,typosquatting,potential-phishing}/search`, `/oem/whois/{lookup,search}`, `/oem/vulnerability-intelligence/{vulnerability-search,exploits-search,advisories-search,feed}`, `/oem/on-demand-scan[/scan-status]`, `/oem/account/{credits,audit-logs}` | see reference |

## Safety rules

- **Write routes are destructive.** `DELETE /enterprise/organizations/{id}` deletes the org and everything under it (users, assets, alerts, vulnerabilities, potential and suggested domains, asset groups). Never call an enterprise POST/PUT/DELETE without the user confirming the exact target.
- **Scans are active.** On-demand scan routes queue real scanning and consume credits. Confirm the user owns or is authorized to scan the target.
- **Dark-web results contain credentials.** Summarize counts, sources and dates. Do not echo passwords or hashes unless the user explicitly needs them.

## Usage patterns

```bash
# GET
curl -s "$FH_API/domain/example.com/subdomains" "${H[@]}" | jq '.hosts'

# Global search: filters are ANDed; page is 1-based; limit default 50, max 200
curl -s "$FH_API/global/search" "${H[@]}" -H "Content-Type: application/json" \
  -d '{"country_code": "GB", "product": "Citrix-NetScaler", "page": 1, "limit": 50}' \
  | jq '{total: .total_query_results, pages: .total_pages, hosts: [.results[].host]}'

# OEM: POST JSON; optional query_tags are recorded in your audit log
curl -s "$FH_API/oem/darkweb/search" "${H[@]}" -H "Content-Type: application/json" \
  -d '{"type": "email", "query": "user@example.com", "query_tags": {"client": "acme"}}' | jq '.response | length'

# Poll an OEM scan
while :; do
  S=$(curl -s "$FH_API/oem/on-demand-scan/scan-status" "${H[@]}" -H "Content-Type: application/json" \
      -d '{"scan_id": "UUID"}' | jq -r '.response.scan_info.status')
  [ "$S" = scan_completed ] && break; sleep 30  # the only terminal status, failures included
done
```

## Response shapes differ by family

There is no single envelope. Parse per family:

| Family | Shape |
|---|---|
| domain details / subdomains | `{domain, hosts[], metadata{...}, whois_data, status, message}` |
| host | host object plus `raw` |
| intel | `{results[], query, total_query_results, credits}` |
| global search | `{results[], query, total_query_results, total_pages, page_size, sort, credits}`; results are flat host records (`asn`, `country_code`, `dns_a`…), not the host object |
| nexus | `{status, error, data, count}`; ip-lookup is `{result, query, resolved_host, resolvable, other_ips}`; whois lookup is `{domain, whois_data}` |
| vuln / exploit / advisory / org search | `{response: [...]}` |
| vuln feed | `{metadata{...}, vulnerabilities[], exploits[], advisories[]}` |
| enterprise orgs, alerts, vulns, entities, assets | bare JSON array |
| enterprise certs, discovered-emails, phishing, typosquatting | `{..., results: {items[], total, page, per_page, pages}}` |
| enterprise compromised-credentials, suggested-domains | `{total_results, page, ..., results[]}` |
| OEM | mostly `{response: ...}`; whois lookup `{domain, whois_data}`; whois search, vulnerabilities, alerts, historical-hosts `{..., total_results, results}`; typosquatting and phishing `{base_domain, total, ...}`; the feed is unwrapped |

Errors come in several shapes, so check `.message`, `.error` and `.status`:
`{"message": ..., "success": false}` (auth), `{"status": N, "message": ...}`, `{"status": N, "error": ...}`, `{"error": ...}` (OEM and validation).
429 returns `{"error": "Rate Limit Exceeded", "message": ...}`. No `X-RateLimit-*` headers are sent, so back off exponentially (start at about 10s).
Some errors are not JSON and break `jq`: 413 (body over 1 MiB) and invalid-JSON 400s are HTML, and global search with no filters returns an empty 400. Check the HTTP status first.

## Known API quirks (current behavior; plan around them)

- **Some Nexus failures return HTTP 200:** tor/check-ip (invalid IP), cloud-certs/dns-search (query under 3 chars), domain-collection/lookup (not found), company-lookup (under 3 chars or not found). Check the body's `status`.
- **Intel routes are not paginated.** `page` is ignored; one response holds everything up to 100 (non-enterprise) or 10,000 (enterprise) results.
- **`/domain/{d}/subdomains?resolvable_only=0` has no effect.** Only resolvable hosts are returned.
- **Nexus whois/search ORs registrar, nameserver, status and expiry** (`tld` is ANDed). **OEM whois/search ANDs everything.** Use OEM when every condition must hold.
- **Enterprise alerts** return 500 per page with no total. Page until you get an empty array.
- **Six OEM routes** (attack-surface/search, organizations/search, darkweb/search, and the vulnerability, exploit and advisory searches) are limited to 100/hour and 1000/day.
- **Vuln, exploit and advisory search return at most 10 results** (OEM: 50). Refine the query instead of paging.
- **CVE IDs are case-sensitive** in vulnerability and exploit search: send `CVE-…` uppercase.
- **Advisory `package` is `ecosystem/name`** (`npm/lodash`); a bare name matches nothing.
- **POST vuln/exploit/advisory search reads form fields only**; use GET query params (a JSON body is ignored).
- **Global search inputs:** use `http_title` (not `http.title`); send `asn`, `port`, `http_status_code`, `page` and `limit` as JSON numbers.

## Workflow guidance

1. `auth/status` first: know the tier and credits.
2. Use the narrowest call: `/subdomains` (names) before `/details` (full objects), and `/host` only for hosts you need.
3. IP enrichment: `nexus/ip-lookup`, then `intel/ip-to-hosts`. WHOIS: `nexus/whois/lookup`.
4. CVE triage: `vulnerability-search` (an uppercase CVE ID is an exact match), then `exploits-search`, then `advisories-search` for package ecosystems.
5. Monitoring: `vulnerability-intelligence/feed?days=1&type=all&keywords=vendor1,vendor2`.

## References

- `references/endpoints.md`: every route with params, limits, response fields, tier and credits
- `references/agentic-ai.md`: MCP setup and the full tool list
