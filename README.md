<h1 align="center">fullhunt-skill</h1>
<h4 align="center">AI skill for querying the FullHunt attack surface intelligence API</h4>

<p align="center">
<a href="https://fullhunt.io"><img src="https://img.shields.io/badge/fullhunt.io-API-purple"></a>
<a href="https://github.com/fullhunt/fullhunt-skill/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue"></a>
</p>

![](https://dkh9ehwkisc4.cloudfront.net/static/files/107a6edf-a338-4f1b-b54c-154688fb2c52-mcp%20blog%20post%20-%201.png)

# What is this

An AI skill that teaches coding assistants how to use the [FullHunt](https://fullhunt.io) API. Install it in Claude Code, Cursor, Windsurf, or any tool that supports Agent Skills, and the assistant can query domains, hosts, vulnerabilities, dark web data, and more through natural language.

The skill gives the assistant a full endpoint reference (tiers, credits, rate limits, response shapes, known quirks), usage patterns, and jq recipes so it can make API calls with `curl` on your behalf.

FullHunt also hosts an MCP server at `https://fullhunt.io/api/v1/mcp` (paid plans). Setup for Claude Code, Cursor, and Claude Desktop plus the full 65-tool list are in [`fullhunt/references/agentic-ai.md`](fullhunt/references/agentic-ai.md). For the full MCP (Model Context Protocol) documentation, see [docs.fullhunt.io](https://docs.fullhunt.io/docs/agentic-ai/).

# Features

- Full coverage of the FullHunt API: domain intel, host details, subdomain enumeration, on-demand scanning.
- Vulnerability intelligence: CVE search, exploit search (ExploitDB, Metasploit), OSV/GHSA advisory search, and the daily vulnerability intelligence feed.
- Dark web monitoring: compromised credentials, discovered emails, phishing domains, typosquatting.
- Data intelligence: IP-to-hosts, ASN lookups, DNS record correlation, Tor exit node checks, passive DNS, WHOIS lookup and search.
- Enterprise APIs: organizations, alerts, assets, certificates, suggested domains, plus organization and asset management (with safety rules for destructive calls).
- OEM APIs: white-label attack surface, dark web, WHOIS, platform vulnerabilities, alerts, historical hosts, vulnerability intelligence, scanning, credits, and audit logs.
- Global search with 49 filters (country, product, ASN, port, cloud provider, CDN, DNS, certificate fields, etc.), paginated.

# Setup

You need a FullHunt API key. Set it as an environment variable:

```bash
export FULLHUNT_API_KEY="your-api-key"
```

Verify it works:

```bash
curl -s "https://fullhunt.io/api/v1/auth/status" \
  -H "X-API-KEY: $FULLHUNT_API_KEY" | jq .user_credits
```

# Installation

Import `fullhunt.skill` into your IDE via its skill settings, or drop the `fullhunt/` folder into your project directory.

**Claude Code:** copy `fullhunt/` to `~/.claude/skills/fullhunt/` (personal) or `.claude/skills/fullhunt/` (project).

**Cursor:** Settings > Skills > Import `fullhunt.skill`

# Usage

Once the skill is installed, just ask questions in natural language:

```
"Find all subdomains of example.com"
"Look up host details for api.example.com"
"Search for CVE-2024-1234 and check if exploits exist"
"Check if 8.8.8.8 is a Tor exit node"
"Show compromised credentials for @acme.com from the dark web"
"Scan example.com for exposed services"
"What organizations are associated with uber.com?"
```

The assistant will pick the right API endpoints and return structured results.

# What's included

```
fullhunt.skill              # Skill package
fullhunt/
├── SKILL.md                # Main skill definition (endpoint table, usage patterns, jq recipes)
└── references/
    ├── endpoints.md        # Full API reference with request/response schemas
    └── agentic-ai.md       # MCP tool reference and multi-step query workflows
CHANGELOG.md
```

After editing `fullhunt/`, rebuild the package: `rm -f fullhunt.skill && zip -r fullhunt.skill fullhunt`

# API coverage

| Category | Endpoints |
|---|---|
| Domain intelligence | Domain details, subdomain enumeration |
| Host intelligence | Host lookup, IP metadata, port/service info |
| Vulnerability intelligence | CVE search, exploit search, advisory search, intelligence feed |
| Data intelligence | IP-to-hosts, ASN, DNS MX/NS correlation, tags, products, web tech |
| Nexus | Tor check, passive DNS, cloud cert search, IP lookup, domain collection, WHOIS lookup/search |
| Attack surface | On-demand scanning (domain, IP, CIDR; enterprise) |
| Organizations | Company search by name or domain |
| Global search | 49-filter search across all indexed hosts (any key with credits) |
| Enterprise | Orgs, alerts, vulns, entities, assets, certs, suggested domains, org/asset management |
| Dark web | Compromised credentials, emails, phishing, typosquatting |
| OEM | Attack surface, orgs, dark web, WHOIS, vulns, alerts, historical hosts, vuln intel + feed, scanning, account |
| MCP | Hosted server, 65 tools |

# About FullHunt

FullHunt is an attack surface management platform. It lets companies discover their internet-facing assets, monitor them for changes, and scan for vulnerabilities. The API provides programmatic access to all of that data.

More info: [https://fullhunt.io](https://fullhunt.io)

# License

MIT License.

# Author

*Mazin Ahmed*

- Email: *mazin at FullHunt.io*
- FullHunt: [https://fullhunt.io](https://fullhunt.io)
- Website: [https://mazinahmed.net](https://mazinahmed.net)
- Twitter: [https://twitter.com/mazen160](https://twitter.com/mazen160)
- LinkedIn: [https://linkedin.com/in/infosecmazinahmed](https://linkedin.com/in/infosecmazinahmed)
