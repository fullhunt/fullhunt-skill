# Defensive Self-Check Recipes

Credit-aware workflows for checking **your own** domains and hosts with the FullHunt API, built only from routes documented in `endpoints.md`. Use them when the user asks for an exposure review, a "what can an attacker see of my domain" check, or a pre-pentest inventory.

All examples assume the variables from `endpoints.md`:
```bash
export FH_API="${FULLHUNT_BASE_URL:-https://fullhunt.io/api/v1}"
H=(-H "X-API-KEY: $FULLHUNT_API_KEY")
```

## Ground rules

- **Own assets only.** These recipes read passive data, but confirm the user owns or is authorized to assess the domain before starting. Never use them to profile a third party.
- **Budget first.** Every data call costs one credit per request, not per result. Run Recipe 0, state the plan ("this will use 5 credits"), then proceed. Do not loop over every subdomain with `/host/{host}` (10/min, 1 credit each); pick the interesting ones.
- **Stop on 403.** A 403 names a missing entitlement or empty credit balance. Do not retry.
- **Check the body on Nexus routes.** Several return HTTP 200 with the error in the body (see `endpoints.md` section 9).

## Recipe 0: Preflight (no credit)

```bash
curl -s "$FH_API/auth/status" "${H[@]}" | jq '.user_credits | {remaining: .remaining_credits, per_month: .total_credits_per_month, cap: .max_results_per_request}'
```
Stop if `remaining` is lower than the number of calls planned. `cap` tells you whether results will be truncated (100 visitor, 500 free, 100000 paid).

## Recipe 1: Subdomain inventory (1 credit)

```bash
D=example.com
curl -s "$FH_API/domain/$D/subdomains" "${H[@]}" \
  | jq '{total: .metadata.all_results_count, returned: .metadata.available_results_for_user, hosts: .hosts}'
```
If `total` is larger than `returned`, the list is truncated by tier. Say so in the report instead of presenting it as complete.

Review the names for forgotten or unexpected entries (`staging`, `dev`, `old`, `vpn`, `test`, `admin`). Those are the usual takeover and exposure candidates.

## Recipe 2: What is live and what is open (1 credit)

```bash
curl -s "$FH_API/domain/$D/details" "${H[@]}" \
  | jq '[.hosts[] | select(.is_live) | {host, ip: .ip_address, status: .http_status_code, title: .http_title, ports: .network_ports, cdn: .cdn, cloud: .cloud.provider}]'
```
One call returns full host objects for the whole domain, so prefer it over per-host lookups. Flag:
- hosts with ports other than 80 and 443 (`ports` containing anything else)
- hosts that are live with no CDN while the rest sit behind one
- unexpected `http_title` values such as default server pages or admin panels

For one host in depth (1 credit, 10/min), use `GET /host/{host}` and read `cert_object` and `products`:
```bash
curl -s "$FH_API/host/api.$D" "${H[@]}" \
  | jq '{ip: .ip_address, ports: .network_ports, products, cert: (.cert_object | {cn: .subject_common_name, expires: .not_after, valid: .is_valid_hostname})}'
```
Report certificates that are expired, expiring soon, or whose `is_valid_hostname` is false.

## Recipe 3: Are the exposed products vulnerable? (1 credit per query)

Take product names from Recipe 2 and look them up. Text searches return at most 10 records, so keep queries specific (3 to 100 characters).

```bash
# Text search by product
curl -s "$FH_API/vulnerability-intelligence/vulnerability-search?query=Citrix%20NetScaler" "${H[@]}" \
  | jq '.response | sort_by(-(.epss_score // 0)) | .[] | {cve: .cve_id, cvss: .cvss_v3_score, epss: .epss_score, kev: .is_kev, exploit: .is_exploit_available}'

# Exact CVE (uppercase, case-sensitive)
curl -s "$FH_API/vulnerability-intelligence/vulnerability-search?query=CVE-2024-3400" "${H[@]}" \
  | jq '.response[] | {cve: .cve_id, kev: .is_kev, exploit: .is_exploit_available, due: .cisa_action_due}'
```
Prioritise records with `is_kev: true` (known exploited), then high `epss_score`, then `is_exploit_available`. A server-side error returns `{response: []}`, so an empty list does not prove a product is safe. Say "no match found" rather than "not vulnerable".

Public exploit code for a confirmed CVE:
```bash
curl -s "$FH_API/vulnerability-intelligence/exploits-search?query=CVE-2024-3400" "${H[@]}" | jq '.response | length'
```
Report that exploit code exists and where (`type`, `platform`, `verified`). Do not paste exploit code into the answer.

## Recipe 4: Triage an unfamiliar IP or domain (1 credit each)

For an address that showed up in your logs or in another tool's output:
```bash
curl -s "$FH_API/nexus/ip-lookup?query=203.0.113.7" "${H[@]}" | jq '.result | {org: .organization, asn, country: .country_name, cloud: .cloud_provider, cdn: .is_cdn}'
curl -s "$FH_API/nexus/tor/check-ip?ip=203.0.113.7" "${H[@]}" | jq '{status, tor: (.count == 1), first_seen: .data.first_seen}'
curl -s "$FH_API/nexus/whois/lookup?domain=example.org" "${H[@]}" | jq '.whois_data'
```
For `tor/check-ip` read `.status`, not the HTTP code. `whois_data` can be `null` when not collected yet; that is not an error.

## Recipe 5: Pair with a passive SpiderFoot scan

SpiderFoot ships a `sfp_fullhunt` module that takes the same API key. Set `FULLHUNT_API_KEY` in its module settings, then run a Passive-use-case scan against your domain. SpiderFoot correlates FullHunt hosts with its other sources (certificates, DNS, breach data), which is a good cross-check for Recipe 1 and 2. Keep the key in SpiderFoot's settings, never in a committed file.

## Reporting template

Keep the output short and decision-ready:

1. **Scope and credits used** (domain, number of calls).
2. **Findings by priority**: KEV or exploitable products first, then expired or invalid certificates, then unexpected open ports and forgotten subdomains.
3. **Truncation or gaps**: tier caps, empty vulnerability responses, null WHOIS.
4. **Next step per finding** (patch, close port, remove DNS record, renew certificate).
