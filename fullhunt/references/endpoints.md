# FullHunt API Endpoints Reference

Verified against the FullHunt API v1 (2026-09-30).

All examples assume:
```bash
export FH_API="${FULLHUNT_BASE_URL:-https://fullhunt.io/api/v1}"   # or https://enterprise-api.fullhunt.io/api/v1
H=(-H "X-API-KEY: $FULLHUNT_API_KEY")
J=(-H "Content-Type: application/json")
```

Columns used below: **Tier** = access gate; **Credit** = what one request consumes; **Rate** = per-account limit (keyed on the account, falling back to client IP). Routes without their own limit get the service default of **100/hour and 1000/day**.

## Contents
1. [Account and public](#1-account-and-public)
2. [Domain](#2-domain)
3. [Host and host object](#3-host-and-host-object)
4. [On-demand scan](#4-on-demand-scan)
5. [Organizations DB](#5-organizations-db)
6. [Vulnerability intelligence](#6-vulnerability-intelligence)
7. [Data intelligence (intel)](#7-data-intelligence-intel)
8. [Global search](#8-global-search)
9. [Nexus](#9-nexus)
10. [Enterprise: read](#10-enterprise-read)
11. [Enterprise: dark web](#11-enterprise-dark-web)
12. [Enterprise: management (write)](#12-enterprise-management-write)
13. [OEM](#13-oem)
14. [Errors, rate limits, pagination](#14-errors-rate-limits-pagination)

---

## 1. Account and public

### Auth status
`GET /auth/status`. Tier: any key. Credit: none. Rate: 60/min.
```bash
curl -s "$FH_API/auth/status" "${H[@]}" | jq .
```
- `user`: `{email, company, first_name, last_name}` (no plan field)
- `user_credits`: `{remaining_credits, total_credits_per_month, credits_usage (= total − remaining), max_results_per_request}`
- `max_results_per_request` reflects the tier: 100 visitor, 500 free, 100000 paid.
- Also carries `status` and `message`. 401 returns `{"status": 401, "message": "Unauthorized"}`.

### My IP
`GET /public/my-ip`. No auth. Credit: none. Rate: 60/min. Returns `{current_ip_address}`.

---

## 2. Domain

Both routes: Tier any key. Credit 1, charged before the lookup. Rate 200/hour. Results are capped by tier (visitor 100, free 500, paid 100,000) and sorted by `last_seen` descending.

### Domain details
`GET /domain/{domain}/details[?resolvable_only=1]`
```bash
curl -s "$FH_API/domain/example.com/details" "${H[@]}" \
  | jq '{total: .metadata.all_results_count, returned: .metadata.available_results_for_user, live: [.hosts[] | select(.is_live) | .host]}'
```
Response: `{domain, hosts[] (host objects, see §3), metadata, whois_data, status, message}`.
`metadata`: `all_results_count`, `available_results_for_user`, `max_results_for_user`, `last_scanned`, `user_plan`, `timestamp`, `domain`.

### Subdomains
`GET /domain/{domain}/subdomains`. Same as details, but `hosts` is an array of hostname strings.

`resolvable_only` is accepted but currently has no effect: only resolvable hosts are returned.

**Errors (both):**
- 400 `invalid_domain` or `credit_limit_reached`; details also returns 400 `redacted_domain_requested` (subdomains returns 404 for redacted domains)
- 404 `domain_not_found` (also returned for excluded, oversized (≥100k hosts) or unresolvable domains; the oversized and unresolvable 404s are still charged)
- 401

---

## 3. Host and host object

### Host
`GET /host/{host}`. Tier any key. Credit 1 (only if found). Rate 10/min.
```bash
curl -s "$FH_API/host/api.example.com" "${H[@]}" | jq '{ip: .ip_address, ports: .network_ports, live: .is_live, cert_cn: .cert_object.subject_common_name}'
```
Returns the host object below plus `raw` (the untransformed database document). Errors: 404 "resource not found", 400 `credit_limit_reached`.

### Host object
Used by domain details, host and enterprise assets. (Global search returns raw database documents instead; see §8.)

| Field | Content |
|---|---|
| `host`, `domain`, `tld` | names |
| `ip_address` | IPv4 |
| `http_status_code`, `http_title` | HTTP probe |
| `is_live`, `is_resolvable`, `is_cloud`, `is_cdn`, `is_cloudflare`, `has_ipv6`, `has_private_ip` | booleans |
| `cdn` | CDN name |
| `cloud` | `{provider, region}` |
| `dns` | `{a, aaaa, cname, mx, ns, ptr, txt}` (arrays) |
| `cert_object` | `subject_common_name`, `subject_organization`, `subject_country`, `subject_province`, `subject_locality`, `issuer_common_name`, `issuer_organization`, `issuer_country`, `issuer_serial_number`, `issuer_string`, `not_before`, `not_after`, `dns_names[]`, `ip_addresses[]`, `email_addresses`, `is_valid_hostname`, `signature_algorithm`, `md5_fingerprint`, `sha1_fingerprint`, `sha256_fingerprint`, `remote_ip_address` |
| `ip_metadata` | `asn`, `organization`, `isp`, `country_code`, `country_name`, `city_name`, `region`, `postal_code`, `location_latitude`, `location_longitude` |
| `network_ports` | int array |
| `network_services[]` | per-port records (port, service, banner, product, TLS/HTTP details) as stored |
| `products[]`, `web[]`, `tags[]`, `categories[]`, `urls[]` | detections |
| `extracted` | extracted artefacts |
| `last_seen` | Unix timestamp |

```bash
| jq '.cert_object | {cn: .subject_common_name, issuer: .issuer_common_name, expires: .not_after, valid: .is_valid_hostname}'
| jq '.ip_metadata | {asn, org: .organization, country: .country_name}'
```

---

## 4. On-demand scan

`GET /attack-surface/on-demand-scan?target=`. **Tier: enterprise account.** Credit 1. Rate 10/min.
- `target`: domain, IP or public CIDR
- Response: `{status, message, target, type, scan_id, timestamp}` (`type` is always `"domain"`; there is no `deduplicated` field)
- A repeat of the same target within 24h reuses the existing scan and is not charged.
- Results land in the database after processing. This triggers **active scanning**.
- Errors: 400 invalid target; 403 no credits (`{"error": "You have no remaining credits for scan requests"}`); 500 if the scan queue is unavailable.

For enterprise-owned assets see `/enterprise/on-demand-scans` (§10); for OEM see §13.

---

## 5. Organizations DB

`GET /organizations-db/search?query=`. Tier any key. Credit: 1 (403 with no credits left; rejected or failed requests are not charged). Rate 60/min.
- `query`: 3–100 chars; matches name, domain, aliases, subsidiaries, stock symbol.
- Response: `{response: [{domain, company_name, other_names[], subsidiaries[{name, domain}], stock_info{stock_symbol, exchange}, other_domains[]}]}`
- Errors: 400 `{"error": "Missing required parameter: query"}` or a length error.

---

## 6. Vulnerability intelligence

### Vulnerability (CVE) search
`GET|POST /vulnerability-intelligence/vulnerability-search?query=`. Tier any key. Credit: 1 (403 with no credits left; rejected or failed requests are not charged). Rate 60/min. **Max 10 results.**
- `query` (3–100 chars):
  - a `CVE-YYYY-NNNN` ID gives an exact match
  - a full CPE string matches an entry of `cpe_ids` exactly (no prefix match)
  - anything else runs a text search
- POST accepts a form-encoded `query` only; a JSON body is ignored (400 "Missing required parameter").
- CVE IDs are matched case-sensitively here and in exploits search: send them uppercase (`CVE-2024-3400`).
- Response: `{response: [...]}`, NVD records with `cve_id`, `title`, `description`, `published_date`, `last_modified_date`, `cvss_v3_score`, `cvss_v3_vector`, `cvss_v2_score`, `cvss_v2_vector`, `cwes[]`, `cpe_ids[]`, `epss_score`, `epss_percentile`, `is_exploit_available`, `is_kev`, `vuln_status`, `source_identifier`, `cisa_exploit_add`, `cisa_action_due`, `cisa_required_action`, `references[]{url, source, tags[]}`.
- Backend errors return `{response: []}`, not an error code.

```bash
curl -s "$FH_API/vulnerability-intelligence/vulnerability-search?query=CVE-2024-3400" "${H[@]}" \
  | jq '.response[] | {cve: .cve_id, cvss: .cvss_v3_score, epss: .epss_score, kev: .is_kev, exploit: .is_exploit_available}'
```

### Exploits search
`GET|POST /vulnerability-intelligence/exploits-search?query=`. Tier any key. Credit: 1 (403 with no credits left; rejected or failed requests are not charged). Rate 60/min. Max 10.
- `query`: 3–100 chars.
- Records (ExploitDB and Metasploit): `edb_id`, `cve_id`, `title`, `author`, `type`, `platform`, `date_published`, `date_added`, `date_updated`, `verified`, `epss_score`, `is_kev`, `file_path`, `codes`, `aliases`, `source_url`, `application_url`, `screenshot_url`. Metasploit records add `module_path`, `full_name`, `rank`, `disclosure_date`, `rport`, `arch`.

### Advisories search (OSV / GHSA)
`GET|POST /vulnerability-intelligence/advisories-search`. Tier any key. Credit: 1 (403 with no credits left; rejected or failed requests are not charged). Rate 60/min. Max 10.
- `query` (3–100 chars), `ecosystem` (npm, PyPI, Go, crates.io, Maven…) and `package` **as `ecosystem/name`** (e.g. `npm/lodash`; a bare `lodash` matches nothing). At least one is required.
- IDs starting `GHSA-`, `PYSEC-`, `RUSTSEC-`, `GO-`, `GSD-`, `OSV-` or `MAL-` are matched exactly.
- Response: `{response: [...]}`.
```bash
curl -s "$FH_API/vulnerability-intelligence/advisories-search?ecosystem=npm&package=npm/lodash" "${H[@]}" | jq '.response | length'
```

### Vulnerability intelligence feed
`GET /vulnerability-intelligence/feed`. **Tier: paid plan or OEM.** Credit 1. Rate 30/min.

| Param | Values |
|---|---|
| `days` | 1–7 (default 1) |
| `page`, `per_page` | `per_page` 1–100 (default 20) |
| `type` | `vulnerabilities`, `exploits`, `advisories`, `all` |
| `keywords` | comma-separated, max 20; a CVE ID gives an exact lookup and ignores the date window |
| `source`, `ecosystem`, `package` | filters (`package` as `ecosystem/name`, e.g. `npm/lodash`) |

- Response: `{status, message, metadata{total_results, total_vulnerabilities, total_exploits, total_advisories, page, per_page, days, cutoff_epoch, type, keywords}, vulnerabilities[], exploits[], advisories[]}`
- Each list is paginated independently.
- Error: 400 `credit_limit_reached`.

---

## 7. Data intelligence (intel)

`GET /intel/{route_type}`. Tier any key; **enterprise keys also need the Data Intelligence module** (403 "Data Intelligence module is not enabled"). Credit 1 (a host 404 is not charged). Rate 60/min.

| route_type | Required param |
|---|---|
| `host` | `host` |
| `domain` | `domain` |
| `tag` | `tag` (ssh, https, rdp, mysql…) |
| `web-tech` | `tech` (URL-encode, e.g. `HTTP%2F3`) |
| `product` | `product` (e.g. `Citrix-NetScaler`) |
| `ip-to-hosts` | `ip` |
| `ip-range-to-hosts` | `ip_start`, `ip_end` |
| `asn-to-hosts` | `asn` (int) |
| `asn-to-virtual-hosts` | `asn` (int) |
| `dns-mx-to-hosts` | `dns_mx` (trailing dot, e.g. `mx1.example.com.`) |
| `dns-ns-to-hosts` | `dns_ns` (trailing dot) |

- Response: `{results[{host, domain, ip_address, dns_ptr, asn, organization}], query{...}, total_query_results, credits}`
- **Not paginated.** `page` is ignored. You get up to 100 results (non-enterprise) or 10,000 (enterprise) in one response, and `total_query_results` is the count returned.
- Errors: 422 for a missing or invalid param or an unknown type; 403 when credits are exhausted.

```bash
curl -s "$FH_API/intel/asn-to-hosts?asn=15169" "${H[@]}" | jq '{n: .total_query_results, sample: .results[:5]}'
```

---

## 8. Global search

`POST /global/search` (JSON body). Tier: any key with credits. Credit 1 per request. Rate 60/min.

**Enterprise accounts** are gated by the Global Search module:
- The module must be enabled (403 "Global Search module is not enabled").
- If the account has a filter allow-list, every filter must be on it, with aliases checked by canonical name (403 "Filter not enabled for your account: ..."). No allow-list means all filters.
- The credit comes from the module's own pool (403 "You have no remaining Global Search credits"); the response's `credits` is that pool's balance.
- With the module's vulnerability-access flag, results include each host's `vulnerabilities`.

**Body:** any filters from the list below, plus `page` (1-based) and `limit` (default 50, max 200). All filters are ANDed.

| Group | Filters |
|---|---|
| Names | `domain`, `host`, `subdomain`, `tld` |
| Network | `ip`, `port`, `asn`, `organization`, `service`, `cdn`, `cloud_provider`, `cloud_region` |
| Geo | `country_code`, `country`, `city` |
| HTTP | `http_title`, `http.title`, `http_status_code`, `http_favicon_hash` |
| Technology | `tech`, `product`, `tag` |
| DNS | `dns_a`, `dns_aaaa`, `dns_cname`, `dns_mx`, `dns_txt`, `dns_ptr`, `dns_ns` |
| Flags | `is_cloud`, `is_live`, `is_resolvable`, `is_cdn`, `is_dos_defense`, `has_ipv6`, `has_private_ip` |
| Certificate issuer | `cert_issuer_common_name`, `cert_issuer_organization`, `cert_issuer_country`, `cert_issuer_serial_number`, `cert_signature_algorithm` |
| Certificate subject | `cert_subject_common_name`, `cert_subject_country`, `cert_subject_province`, `cert_subject_locality`, `cert_subject_organization` |
| Certificate fingerprints | `cert_md5_fingerprint`, `cert_sha1_fingerprint`, `cert_sha256_fingerprint` |

**Aliases:** `tags` means `tag`, `technology` means `tech`, `ip_address` means `ip`, `city_name` means `city`.

```bash
curl -s "$FH_API/global/search" "${H[@]}" "${J[@]}" \
  -d '{"product": "Citrix-NetScaler", "country_code": "GB", "is_live": true, "limit": 100}' \
  | jq '{total: .total_query_results, pages: .total_pages, hosts: [.results[].host]}'
```
- Response: `{results[] (raw host documents plus `id`: flat `asn`, `organization`, `country_code`, `cloud_provider`, `dns_a`…, raw `cert_object` keys such as `subject_commonname`; no `ip_metadata`/`cloud{}`/`dns{}`; without vulnerabilities, visual_hash or type), query, total_query_results (capped at 10M; 10000 if the count times out), total_pages, page_size, sort ("asset_score" or "natural"), credits}`
- Ranked sorting has an 8-second budget, then falls back to natural order.
- Errors: 422 "Incorrect filter: x" for an unknown filter; 400 with an **empty body** if no filters are given, and an HTML 400 for invalid JSON; 403 when credits are exhausted or the key is unauthorized.
- Silent no-ops: `http.title` is accepted but ignored (use `http_title`); non-numeric `asn`, `port` and `http_status_code` are dropped; `page` and `limit` must be JSON integers (`"100"` falls back to 50); `is_dos_defense` matches the strings `"true"`/`"false"`.

---

## 9. Nexus

Tier any key. Credit 1 on success. Rate 60/min unless noted. Credit exhaustion returns 403 `{status, error}`.

| Route | Params | Response |
|---|---|---|
| `GET /nexus/ip-lookup` | `query` (IP or hostname; hostnames are resolved) | `{result{asn, organization, isp, country_code, country_name, city_name, postal_code, cloud_provider, cloud_region, cdn_provider, cdn_region, is_cdn, is_cloud, is_cloudflare, is_private, is_public, is_ipv4, is_ipv6, ip_decimal, ptr[], location_latitude, location_longitude, hosts_count}, query, resolved_host, resolvable, other_ips}`. Errors: 422, and 502 if the upstream fails. |
| `GET /nexus/tor/check-ip` | `ip` | `{status, error, data{ip_address, first_seen}, count}`; `count` is 1 if Tor |
| `GET /nexus/cloud-certs/dns-search` | `query` (at least 3 chars, prefix match) | `{status, count, data[{dns[], host, port}]}`, up to 10,000 |
| `GET /nexus/passive-dns/lookup` | `domain` | `{status, count, data[] (hostnames, up to 10k)}` |
| `GET /nexus/domain-collection/lookup` | `domain` | `{status, data{company_name, description, title, meta_logo_url, *_urls social links}}` |
| `GET /nexus/domain-collection/company-lookup` | `query` | `{status, data[{company_name, domain}]}` (10 results, text search) |
| `GET /nexus/whois/lookup` | `domain` | `{domain, whois_data}`; `whois_data` is `null` if not collected yet |
| `GET /nexus/whois/search` (30/min) | `registrar`, `nameserver`, `tld`, `status`, `expires_before` (ISO date), `limit` (≤10); at least one filter | `registrar`, `nameserver`, `status` and `expires_before` are ORed (any match); `tld` is ANDed with them. 422 if no filter. |

**Some Nexus failures return HTTP 200 with the error in the body, and are charged:** tor/check-ip (invalid IP: text in `message`), cloud-certs/dns-search (query under 3 chars), domain-collection/lookup (not found) and company-lookup (under 3 chars, or not found). Check the body's `status`, not the HTTP code. Empty or invalid input on cloud-certs and domain-collection returns a real 422.

```bash
curl -s "$FH_API/nexus/ip-lookup?query=8.8.8.8" "${H[@]}" | jq '.result | {org: .organization, asn, country: .country_name, cloud: .cloud_provider}'
curl -s "$FH_API/nexus/whois/lookup?domain=example.com" "${H[@]}" | jq '.whois_data'
```

---

## 10. Enterprise: read

Tier: enterprise account. No credits. Scoped to the caller's organizations. Dates use `DD/MM/YYYY` (day first).

| Route | Rate | Params | Response |
|---|---|---|---|
| `GET /enterprise/organizations` | 20/min | none | bare array `[{id, name, description, is_default, ...}]` |
| `GET /enterprise/alerts` | 20/min | `org` (organization id from `/enterprise/organizations`), `page`, `from`, `to` | bare array `[{id, type, title, message, host, is_seen, timestamp}]`; **500 per page, no total** (page until empty); 400 `invalid_date` |
| `GET /enterprise/vulnerabilities` | 20/min | `org` | bare array (not paginated, ≤100k) `[{vulnerability_id, vulnerability_type, severity, status, affected_location, description, impact, recommendation, automated_vulnerability_validation_status, ...}]` |
| `GET /enterprise/entities` | 20/min | `org` | `[{asset, type: domain \| ip-range}]` |
| `GET /enterprise/assets` | 20/min | `entity` (required; 422 if missing) | array of host objects (§3); 404 if the entity is unknown |
| `GET /enterprise/suggested-domains` | 60/min | `query`, `page`, `from`, `to` | `{total_results, page, per_page: 1000, total_pages, query, total_query_results, results[{suggested_domain, identification_method, discovery_data}]}` |
| `GET /enterprise/certificates` | 60/min | `q`, `page`, `from`, `to` | `{status, total_results, page, query, total_query_results, results{items[{id, domain_name, date_added, last_seen, type}], total, page, per_page: 10, pages}}`; default org only |
| `GET /enterprise/on-demand-scans` | 10/min | `target`: exactly a domain, IP or CIDR registered to one of your orgs (a subdomain or sub-range gets 403) | `{status, message, target, scan_id, deduplicated}`; 1 credit. 403 no credits or not owned; 422 invalid target; 503 submission disabled. **Active scan.** |

---

## 11. Enterprise: dark web

Tier: enterprise plus the dark-web module (403 "Module is not enabled" otherwise). No credits. Rate 60/min.

| Route | Module | Params | Response |
|---|---|---|---|
| `GET /enterprise/darkweb/compromised-credentials` | dark-web | `query` (email or domain), `page` | `{total_results, page, query, total_query_results, results[{id, email, username, password, hashed_password, hash_type, name, phone, address, ipaddress, vin, domain, database_name, breach_date, date_added, darkweb_metadata_*}]}`; 1000 per page |
| `GET /enterprise/darkweb/discovered-emails` | dark-web | **`q`**, `page` | `{status, query, total_query_results, results{items[{id, email, domain, date_added, breach_date, breaches[], darkweb_metadata_*}], total, page, per_page: 1000, pages}}` |
| `GET /enterprise/darkweb/potential-phishing` | dark-web | `q`, `page`, `from`, `to` | `results{items[], total, page, per_page: 1000, pages}` (all orgs) |
| `GET /enterprise/darkweb/typosquatting` | dark-web | `q`, `page`, `from`, `to` | `results{items[], total, page, per_page: 10, pages}` (default org) |

Results contain credentials. Summarize them and don't echo secrets.

---

## 12. Enterprise: management (write)

Tier: enterprise, plus the matching account permission (403 otherwise). No credits. JSON bodies.
**These change account state. Confirm the exact target with the user before calling.**

| Route | Rate | Body | Result |
|---|---|---|---|
| `POST /enterprise/organizations` | 10/min | `name` (required), `description` | 201 with the org; needs the `add-organization` permission |
| `DELETE /enterprise/organizations/{org_id}` | 10/min | none | **Deletes the org and everything under it** (users, assets, alerts, vulnerabilities, potential domains, asset groups, suggested domains). 400 for the default org; 404 if not found |
| `POST /enterprise/organizations/{org_id}/domains` | 20/min | `domain` | 201 `{status, asset, type: "dns"}`; 409 if another account owns it |
| `POST /enterprise/organizations/{org_id}/ip-ranges` | 20/min | `ip_range` (a bare IP becomes /32) | 201 `{..., type: "ip-range"}`; 409 |
| `DELETE /enterprise/organizations/{org_id}/domains` | 20/min | `domain` | 200; 404 |
| `DELETE /enterprise/organizations/{org_id}/ip-ranges` | 20/min | `ip_range` | 200; 404 |
| `PUT /enterprise/organizations/{org_id}/domains/settings` | 20/min | `domain`, optional `organization_id` (move), `is_global_continuous_scans_enabled`, `is_global_target_notifications_enabled`, `is_redacted_from_community_platform` | 200 |
| `PUT /enterprise/organizations/{org_id}/ip-ranges/settings` | 20/min | `ip_range` plus the same flags | 200 |

---

## 13. OEM

Tier: enterprise plus the OEM module (403 "OEM API is not enabled for your account" otherwise). **All routes are POST with a JSON body.**

Shared behaviour:
- **Credits:** routes marked 1 deduct one OEM credit on a 2xx response, including cache hits. The OEM vulnerability, exploit and advisory searches return 200 `[]` on a backend failure and are charged. When OEM credits are exhausted the route returns 403 `{"error": "You have exhausted your OEM API credits"}`.
- **Optional body fields:** `query_tags` (object) is stored in your audit log. `no_cache: true` bypasses the 24-hour response cache on cached routes.
- **Audit log:** every call that passes validation is recorded.

| Route | Credit | Rate | Body | Response |
|---|---|---|---|---|
| `/oem/attack-surface/search` | 1 | 100/h | `type`: `domain` or `ip_range` (CIDR ≤ 4096 addresses; a bare IP becomes /32); `query` | `{response{domain \| ip_range, hosts[≤10k], metadata, whois_data (domain only)}}`; cached 24h (`no_cache` currently ignored) |
| `/oem/attack-surface/host` | 1 | 60/min | `type`: `host`; `query` (host or IP) | `{response{host, data, metadata}}`; 404 |
| `/oem/organizations/search` | 1 | 100/h | `type`: `domain` or `organization` (**required**); `query` (3–100) | `{response: [orgs]}` (rich profile: executives, HQ, breaches, subsidiaries); cached |
| `/oem/darkweb/search` | 1 | 100/h | `type`: one of username, name, email, hostname, mac_address, ip_address, org_alias, bin, cve, domain, password, hashed_password, vin, address, phone; `query`; `no_cache`; optional `from`/`to` (`DD-MM-YYYY`, inclusive, filters on date added; bad or inverted dates return 400) | `{response: [records with hashed_password[], breach_date, date_added (epoch)]}`; `type=cve` returns the NVD record. Empty result is 200 with `[]`. 404 "API request failed" only when the upstream is down and nothing is cached. Max 15k rows. |
| `/oem/vulnerabilities/search` | 1 | 60/min | `type`: `host`, `domain` or `ip_range`; `query` | `{query{type, value}, total_results, results[≤10k]}` (platform-discovered vulns) |
| `/oem/alerts/search` | 1 | 60/min | `type`: `host` or `domain`; `query` | same shape (alerts ledger) |
| `/oem/historical-hosts/search` | 1 | 60/min | `type`: `host` or `domain`; `query` | same shape (historical host records) |
| `/oem/typosquatting/search` | 1 | 60/min | `query` (base domain) | `{base_domain, total, typosquatting_domains[{domain, base_domain, type, dns, dns_history, last_seen, date_added}]}` |
| `/oem/potential-phishing/search` | 1 | 60/min | `query` (base domain) | `{base_domain, total, potential_phishing_domains[...]}` (Certificate Transparency based) |
| `/oem/whois/lookup` | 1 | 60/min | `domain` | `{domain, whois_data}` |
| `/oem/whois/search` | 1 | 60/min | `registrar`, `nameserver`, `tld`, `status`, `expires_before`, `limit` (≤10) | `{filters, total_results, results}`; filters are **ANDed** |
| `/oem/vulnerability-intelligence/vulnerability-search` | 1 | 100/h | `query` (3–100) | `{response: [≤50 NVD records]}` |
| `/oem/vulnerability-intelligence/exploits-search` | 1 | 100/h | `query`, `no_cache` | `{response: [≤50]}`; cached |
| `/oem/vulnerability-intelligence/advisories-search` | 1 | 100/h | `query`, `ecosystem`, `package`, `no_cache` | `{response: [≤50]}`; cached |
| `/oem/vulnerability-intelligence/feed` | 1 | 60/min | community feed params (§6) plus `severity` (critical, high, medium, low), `kev`, `exploit_available` | feed shape plus those filters in `metadata`; NVD `references` kept |
| `/oem/on-demand-scan` | 1 | 5/min | `type`: `domain`, `ip_range` or `host` (**required**); `target`. Private ranges are rejected with 400 | `{response{status, message, target, type, scan_id, timestamp}}`. **Active scan.** |
| `/oem/on-demand-scan/scan-status` | 0 | 10/min | `scan_id` | `{response{status, scan_info{scan_id, target, status, created_at, completed_at}, timestamp}}`; status goes `queued`, then `*_started`/`*_completed` stages; `scan_completed` is the only terminal status (failed scans end there too); 404 |
| `/oem/account/credits` | 0 | 30/min | `{}` | `{response{credits_remaining, oem_enabled, company, account_id, timestamp}}` |
| `/oem/account/audit-logs` | 0 | 15/min | `page`, `start_date`, `end_date` (`YYYY-MM-DD`) | `{response{logs[] (50 per page), pagination{page, total, total_pages, has_next, has_prev}, timestamp}}` |

```bash
curl -s "$FH_API/oem/attack-surface/search" "${H[@]}" "${J[@]}" \
  -d '{"type": "domain", "query": "acme.com", "query_tags": {"client": "acme"}}' | jq '.response.hosts | length'
curl -s "$FH_API/oem/on-demand-scan" "${H[@]}" "${J[@]}" \
  -d '{"type": "host", "target": "api.acme.com"}' | jq -r '.response.scan_id'
```

---

## 14. Errors, rate limits, pagination

**Status codes:**

| Code | Meaning |
|---|---|
| 400 | Bad input (`invalid_domain`, length errors, `credit_limit_reached` on domain, host and feed) |
| 401 | Missing or invalid `X-API-KEY` |
| 403 | Entitlement: no credits, not a paid plan, not enterprise, OEM or dark-web module off, expired trial. Don't retry. |
| 404 | Not found (also used for redacted or excluded domains) |
| 409 | Asset owned by another account (enterprise write) |
| 413 | Request body over 1 MiB (HTML body) |
| 422 | Missing or invalid parameter (intel, nexus, global search filter) |
| 429 | Rate limited: `{"error": "Rate Limit Exceeded", "message": ...}` |
| 5xx | Retry with backoff; 502 on nexus upstream failure |

**Error body shapes:** `{"message", "success": false}` (auth), `{"status", "message"}`, `{"status", "error"}`, `{"error"}`. Check all of them. Some errors are not JSON: 413 and invalid-JSON 400s are HTML, and global search with no filters returns an empty 400. Unknown paths return `{"error": "Not Found", "message": ...}`.

**Rate limits:**
- Limits are per account.
- No `X-RateLimit-*` headers and no `retry_after` field are sent. Use exponential backoff.
- Routes without an explicit limit get **100/hour, 1000/day**.

**Pagination by route:**

| Route | Page size |
|---|---|
| Global search | `page` and `limit` (≤200) |
| Enterprise alerts | 500 |
| Suggested domains, compromised credentials, discovered emails, phishing | 1000 |
| Enterprise certificates, typosquatting | 10 |
| Vuln feed | `page` and `per_page` (≤100) |
| OEM audit logs | 50 |
| Intel, domain routes, enterprise vulns, entities, assets | not paginated |

Truncation: compare `metadata.all_results_count` with `available_results_for_user` on domain routes.
