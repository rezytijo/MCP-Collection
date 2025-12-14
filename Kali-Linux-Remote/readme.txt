# Penetration Test Playbook MCP Server

A Model Context Protocol (MCP) server that provides secure access to run penetration testing tools on an existing Kali Linux VM via SSH, with template support for tools like Nuclei.

## Purpose

This MCP server provides a secure interface for AI assistants to execute penetration testing commands on a remote Kali Linux VM, supporting customizable templates and generating clean, formatted reports.

## Features

### Current Implementation
- **`check_dependencies`** - Verify all required pentesting tools are installed on Kali VM
- **`run_nuclei_with_template`** - Runs Nuclei scans using specified templates against targets on the connected Kali VM
- **`run_nikto`** - Runs Nikto web server scanner on target URLs
- **`run_sqlmap`** - Runs SQLMap for SQL injection testing on target URLs
- **`run_nmap`** - Runs Nmap port scanner on targets with customizable options
- **`run_web_pentest_playbook`** - Executes comprehensive web penetration testing playbook following industry standards

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- Existing Kali Linux VM accessible via SSH
- SSH credentials (username/password or key-based auth)

## Installation

See the step-by-step instructions provided with the files.

## Usage Examples

In copilot CLI, you can ask:
- "Check if all pentesting tools are installed on the VM"
- "Run a Nuclei scan with the xss template against example.com"
- "Execute Nuclei using the cve-2023 template on target 192.168.1.1"
- "Scan example.com with Nikto"
- "Run SQLMap on http://example.com/vulnerable.php?id=1"
- "Run Nmap port scan on target.com with service detection"
- "Perform complete web pentest playbook on https://target-site.com"

## Architecture

```
copilot CLI → MCP Gateway → Penetration Test Playbook MCP Server → Kali Linux VM (via SSH)
↓
Docker Desktop Secrets
(SSH_HOST, SSH_USER, SSH_PASSWORD or SSH_KEY_PATH)
```

## Development

### Local Testing

```bash
# Set environment variables for testing
export SSH_HOST="your-vm-ip"
export SSH_USER="kali"
export SSH_PASSWORD="your-password"

# Run directly
python pentest_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python pentest_server.py
```

### Adding New Tools

1. Add the function to `pentest_server.py`
2. Decorate with `@mcp.tool()`
3. Update the catalog entry with the new tool name
4. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully
- Check catalog and registry files
- Ensure copilot CLI config includes custom catalog
- Restart copilot CLI

### SSH Connection Errors
- Verify SSH credentials with `ssh user@host` manually
- Ensure VM is accessible and SSH service is running
- Check firewall rules on the VM

## Security Considerations

- All SSH credentials stored in Docker Desktop secrets
- Never hardcode credentials
- Running as non-root user
- Sensitive data never logged
- Input sanitization to prevent command injection

## License

MIT License