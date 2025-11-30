# Penetration Testing MCP Server

A Model Context Protocol (MCP) server that provides AI-assisted access to common penetration testing and security assessment tools.

## ⚠️ CRITICAL WARNING

This server provides access to OFFENSIVE SECURITY TOOLS. Use ONLY on:
- Systems you own
- Systems you have explicit written permission to test
- Isolated lab environments

Unauthorized access to computer systems is ILLEGAL. You are responsible for all actions performed using this server.

## Purpose

This MCP server provides a secure interface for AI assistants to perform security assessments, vulnerability scanning, and penetration testing tasks on authorized systems in controlled lab environments.

## Features

### Current Implementation

- **`nmap_scan`** - Network reconnaissance and port scanning with multiple scan types (basic, fast, intense, stealth, udp, os)
- **`nikto_scan`** - Web server vulnerability scanning and misconfiguration detection
- **`sqlmap_scan`** - SQL injection vulnerability testing for web applications
- **`wpscan_scan`** - WordPress-specific security scanning and enumeration
- **`dirb_scan`** - Directory and file brute force discovery on web servers
- **`searchsploit_query`** - Search ExploitDB database for known exploits
- **`dns_enum`** - DNS enumeration with A, MX, NS, and TXT record gathering
- **`whois_lookup`** - Domain registration information lookup
- **`port_knock`** - TCP port knocking sequence execution
- **`custom_command`** - Execute custom commands with allowed security tools

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- Sufficient system resources (Kali Linux base image is large)
- Isolated lab network for testing

## Installation

See the step-by-step instructions provided with the files.

## Usage Examples

In Claude Desktop, you can ask:

- "Scan 192.168.1.100 with nmap using an intense scan"
- "Run a nikto scan on http://testsite.local"
- "Check http://mywordpress.local for WordPress vulnerabilities"
- "Search for Apache 2.4.49 exploits in searchsploit"
- "Enumerate DNS records for example.com"
- "Run dirb against http://target.local to find hidden directories"
- "Test http://vulnerable-site.local/login.php for SQL injection"

## Architecture
```
Claude Desktop → MCP Gateway → Pentest MCP Server → Security Tools
                                      ↓
                                Kali Linux Container
                            (nmap, nikto, sqlmap, etc.)
```

## Development

### Local Testing
```bash
# Run directly with Python
python3 pentest_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 pentest_server.py
```

### Adding New Tools

1. Install the tool in the Dockerfile
2. Add a new function to `pentest_server.py`
3. Decorate with `@mcp.tool()`
4. Update the catalog entry with the new tool name
5. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully: `docker images | grep pentest`
- Check catalog and registry files
- Ensure Claude Desktop config includes custom catalog
- Restart Claude Desktop completely

### Permission Errors
- Some tools require elevated privileges
- Verify capabilities are set correctly in Dockerfile
- Check container is running as expected user

### Slow Scans
- Security scans can take time (especially sqlmap, wpscan)
- Default timeouts are set conservatively
- Monitor Docker logs: `docker logs <container-name>`

## Security Considerations

- Container runs as non-root user where possible
- Input sanitization on all parameters
- Output truncation to prevent memory issues
- Command timeouts to prevent hung processes
- Only allowed tools can be executed via custom_command
- All activities are logged to stderr

## Legal & Ethical Use

YOU MUST:
- Only scan systems you own or have written authorization to test
- Understand and comply with laws in your jurisdiction
- Use in isolated lab environments
- Not use against production systems without proper approval
- Take responsibility for all actions

## License

MIT License - Use at your own risk