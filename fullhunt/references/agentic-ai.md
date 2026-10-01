# FullHunt Agentic AI / MCP Reference

FullHunt hosts a Model Context Protocol (MCP) server so AI assistants (Claude Code, Claude Desktop, Cursor and other MCP clients) can run FullHunt queries as tools.

## Endpoint and access

| | |
|---|---|
| URL | `https://fullhunt.io/api/v1/mcp` or `https://enterprise-api.fullhunt.io/api/v1/mcp` |
| Transport | Streamable HTTP (stateless) |
| Auth | `X-API-KEY: <key>` or `Authorization: Bearer <key>` |
| Access | Paid plan (builder, scale, professional, consultant, enterprise) or an active enterprise account. Free keys get 403 "FullHunt Agentic AI is only available for paid plans." |
| Rate | 60 requests/min to `/mcp`, plus each tool's own REST rate limit |
| Credits | Each tool call costs what its REST route costs (see `endpoints.md`). `search` is local and costs nothing. |

Individual tools still enforce their REST tier: enterprise tools need an enterprise account, `oem_*` tools need the OEM module.

## Client configuration

### Claude Code
```bash
claude mcp add --transport http fullhunt https://fullhunt.io/api/v1/mcp \
  --header "X-API-KEY: $FULLHUNT_API_KEY"
```

### Cursor
`~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project):
```json
{
  "mcpServers": {
    "fullhunt": {
      "url": "https://fullhunt.io/api/v1/mcp",
      "headers": { "X-API-KEY": "${env:FULLHUNT_API_KEY}" }
    }
  }
}
```

### Claude Desktop
Claude Desktop's JSON config launches local (stdio) servers. Bridge to the remote server with `mcp-remote` (requires Node.js).
Config file: macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows `%APPDATA%\Claude\claude_desktop_config.json`.
```json
{
  "mcpServers": {
    "fullhunt": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://fullhunt.io/api/v1/mcp",
               "--header", "X-API-KEY:${FULLHUNT_API_KEY}"],
      "env": { "FULLHUNT_API_KEY": "your-api-key" }
    }
  }
}
```

### Other clients
Any Streamable-HTTP MCP client: URL above plus the `X-API-KEY` header (or `Authorization: Bearer`).

### Enterprise and OEM accounts
Swap in `https://enterprise-api.fullhunt.io/api/v1/mcp`.

## Verify the connection

Ask the assistant to "check my FullHunt account status". It should call `auth_status` (no credit) and return your profile and credit balance. `public_my_ip` is also a no-credit connectivity check.

## Troubleshooting

- **403 "only available for paid plans"**: the key is on the free tier. Upgrade, or use REST directly.
- **401 / authentication failed**: regenerate the key at https://fullhunt.io/user/settings/, check for stray spaces, and confirm the env var is set in the client's environment (not only your shell).
- **Tool returns 403**: that tool needs a higher tier (enterprise or OEM) or a module (dark web).
- **429**: back off. The MCP endpoint and each REST route have separate limits.

---

## Tools (65)

`?` marks an optional parameter. Tool argument names can differ from REST parameter names; the server maps them (for example `nexus_ip_lookup(ip)` sends `?query=`).

Tool results are the REST JSON, except that bare-array responses (enterprise orgs, alerts, vulnerabilities, entities, assets) arrive as `{"results": [...], "count": n}`. API errors surface as tool errors; a 404 always reads "no data found for that query" and the API's own message is not passed through.

### Discovery (ChatGPT/Deep-Research style)
| Tool | Parameters | Description |
|---|---|---|
| `search` | `query` | Classifies a domain, host, IP, CVE or company name and returns result ids. No API call and no credit. |
| `fetch` | `id` | Expands an id from `search` (`domain:`, `subdomains:`, `whois:`, `host:`, `cve:`, `exploits:`, `advisory:`, `ip:`, `iphosts:`, `org:`). Costs what the underlying route costs. |

### Account and public
| Tool | Parameters | Description |
|---|---|---|
| `auth_status` | none | Profile and credit balance (no plan name; infer the tier from `max_results_per_request`) |
| `public_my_ip` | none | The client IP the API sees for this MCP call (no credit). Equals your IP only if the MCP proxy forwards it |
| `public_0day_today_search` | `query` | 0day.today exploit archive search (10/min, 5 results) |

### Domain and host
| Tool | Parameters | Description |
|---|---|---|
| `fullhunt_domain_details` | `domain` | Domain with full host objects |
| `fullhunt_domain_subdomains` | `domain` | Subdomain names |
| `fullhunt_host` | `host` | Full host object |
| `fullhunt_scan` | `target` | On-demand scan of a domain, IP or CIDR (enterprise account required) |

### Search and vulnerability intelligence
| Tool | Parameters | Description |
|---|---|---|
| `search_organizations` | `query` | Organizations DB (3–100 chars) |
| `search_vulnerabilities` | `query` | CVE search: exact uppercase CVE ID, exact CPE string, or text (3–100 chars, max 10) |
| `search_exploits` | `query` | ExploitDB/Metasploit search (3–100 chars, max 10) |
| `search_advisories` | `query?`, `ecosystem?`, `package?` (`ecosystem/name`, e.g. `npm/lodash`) | OSV/GHSA advisories; at least one parameter (max 10) |
| `vulnerability_intelligence_feed` | `days?`, `page?`, `per_page?`, `type?`, `keywords?`, `source?`, `ecosystem?`, `package?` | Recent vulns, exploits and advisories (paid plan) |

### Data intelligence
| Tool | Parameters |
|---|---|
| `intel_host` | `host` |
| `intel_tag` | `tag` |
| `intel_web_tech` | `tech` |
| `intel_product` | `product` |
| `intel_domain` | `domain` |
| `intel_ip_to_hosts` | `ip` |
| `intel_asn_to_hosts` | `asn` |
| `intel_asn_to_virtual_hosts` | `asn` |
| `intel_ip_range_to_hosts` | `ip_start`, `ip_end` |
| `intel_dns_mx_to_hosts` | `dns_mx` |
| `intel_dns_ns_to_hosts` | `dns_ns` |

Intel responses are not paginated (up to 100 results, or 10,000 for enterprise). Enterprise accounts need the Data Intelligence module.

### Global search
| Tool | Parameters | Description |
|---|---|---|
| `global_search` | any of 47 filters (REST also accepts `http.title` and `is_dos_defense`) (`domain`, `host`, `subdomain`, `tld`, `ip`, `tag`, `organization`, `http_title`, `http_favicon_hash`, `http_status_code`, `country_code`, `country`, `city`, `tech`, `product`, `service`, `port`, `asn`, `cloud_provider`, `cloud_region`, `cdn`, `dns_a/aaaa/cname/mx/txt/ptr/ns`, `cert_*` (13), `is_cloud`, `is_live`, `is_resolvable`, `is_cdn`, `has_ipv6`, `has_private_ip`), plus `page?`, `limit?` (≤200) | Whole-database host search; filters ANDed. |

### Nexus
| Tool | Parameters |
|---|---|
| `nexus_ip_lookup` | `ip` (IP or hostname) |
| `nexus_tor_check_ip` | `ip` |
| `nexus_certs_dns_search` | `dns_name` (at least 3 chars, prefix match) |
| `nexus_passive_dns_lookup` | `domain` |
| `nexus_domain_collection_lookup` | `domain` |
| `nexus_domain_collection_company_lookup` | `company` |
| `nexus_whois_lookup` | `domain` |
| `nexus_whois_search` | `registrar?`, `nameserver?`, `tld?`, `status?`, `expires_before?`, `limit?` (≤10). registrar, nameserver, status and expiry are ORed; `tld` is ANDed. |

### Enterprise (enterprise account)
| Tool | Parameters |
|---|---|
| `enterprise_organizations` | none |
| `enterprise_alerts` | `org?`, `page?`, `from_date?`, `to_date?` (DD/MM/YYYY) |
| `enterprise_vulnerabilities` | `org?` |
| `enterprise_entities` | `org?` |
| `enterprise_assets` | `entity` |
| `enterprise_suggested_domains` | `query?`, `page?`, `from_date?`, `to_date?` |
| `enterprise_on_demand_scans` | `target` (must be an asset you own) |
| `enterprise_certificates` | `q?`, `page?`, `from_date?`, `to_date?` |
| `enterprise_darkweb_compromised_credentials` | `query?`, `page?` (dark-web module) |
| `enterprise_darkweb_discovered_emails` | `query?`, `page?` (dark-web module) |
| `enterprise_darkweb_potential_phishing` | `q?`, `page?`, `from_date?`, `to_date?` (dark-web module) |
| `enterprise_darkweb_typosquatting` | `q?`, `page?`, `from_date?`, `to_date?` (dark-web module) |

The enterprise write routes (create/delete organizations, add/remove domains and IP ranges, settings) are deliberately not exposed as MCP tools. Use REST with explicit confirmation.

### OEM (OEM module; 1 OEM credit per successful call unless noted)
| Tool | Parameters |
|---|---|
| `oem_attack_surface_search` | `target`, `query_type?` (`domain` default, or `ip_range` CIDR ≤ 4096 addresses) |
| `oem_attack_surface_host` | `query` (host or IP) |
| `oem_organizations_search` | `query`, `query_type?` (`domain` default, or `organization`) |
| `oem_darkweb_search` | `query`, `query_type?` (default `email`; no `from`/`to` date filter, use REST for that; one of 15: username, name, email, hostname, mac_address, ip_address, org_alias, bin, cve, domain, password, hashed_password, vin, address, phone) |
| `oem_typosquatting_search` | `query` (base domain) |
| `oem_potential_phishing_search` | `query` (base domain) |
| `oem_vulnerabilities_search` | `query`, `query_type?` (host, domain, ip_range) |
| `oem_alerts_search` | `query`, `query_type?` (host, domain) |
| `oem_historical_hosts_search` | `query`, `query_type?` (host, domain) |
| `oem_whois_lookup` | `domain` |
| `oem_whois_search` | `registrar?`, `nameserver?`, `tld?`, `status?`, `expires_before?`, `limit?` (≤10). Filters are ANDed. |
| `oem_vulnerability_search` | `query` (max 50) |
| `oem_exploits_search` | `query` (max 50) |
| `oem_advisories_search` | `query?`, `ecosystem?`, `package?`, `no_cache?` (max 50) |
| `oem_vulnerability_intelligence_feed` | `days?`, `page?`, `per_page?`, `result_type?` (vulnerabilities, exploits, advisories, all), `keywords?`, `severity?`, `kev?`, `exploit_available?`, `source?`, `ecosystem?`, `package?` |
| `oem_on_demand_scan` | `target`, `query_type?` (`domain` default, `ip_range`, `host`); 5/min |
| `oem_scan_status` | `scan_id` (no credit) |
| `oem_account_credits` | none (no credit) |
| `oem_account_audit_logs` | `page?`, `start_date?`, `end_date?` (YYYY-MM-DD; no credit) |

---

## Multi-step patterns

```
"Investigate acme.com and find exposed admin panels"
→ auth_status → fullhunt_domain_subdomains → fullhunt_host (selected hosts) → correlate http_title/tags

"Is 1.2.3.4 malicious? What points to it?"
→ nexus_ip_lookup → nexus_tor_check_ip → intel_ip_to_hosts → nexus_whois_lookup (for the org's domain)

"Triage CVE-2024-3400"
→ search_vulnerabilities (exact ID; CVSS, EPSS, KEV) → search_exploits → search_advisories
→ enterprise_assets / oem_vulnerabilities_search to check exposure

"Supply-chain: is package X affected?"
→ search_advisories(ecosystem="npm", package="npm/X") → vulnerability_intelligence_feed(type="advisories", package="npm/X")

"Vendor risk for vendor.com" (enterprise)
→ fullhunt_domain_details → search_vulnerabilities (per product found)
→ enterprise_darkweb_compromised_credentials(query="vendor.com") → summarize counts, never raw passwords

"Daily watch on our stack" (paid)
→ vulnerability_intelligence_feed(days=1, type="all", keywords="fortinet,citrix,ivanti")
```

Budget credits before fan-out: each `fullhunt_host` or `intel_*` call is one credit.
