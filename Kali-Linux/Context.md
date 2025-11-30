# Penetration Testing MCP Server - Implementation Context

## Overview

This MCP server provides AI assistants with access to common penetration testing tools through a controlled Docker container interface. It's designed for security professionals and students conducting authorized security assessments in lab environments.

## Technical Architecture

### Base Image: Kali Linux
- Uses `kalilinux/kali-rolling` for access to pre-packaged security tools
- Larger image size (~1-2GB) but includes all necessary tools
- Regular updates through Kali's repositories

### Security Tools Included
1. **nmap** - Network scanner and port discovery
2. **nikto** - Web server vulnerability scanner
3. **sqlmap** - SQL injection testing framework
4. **wpscan** - WordPress security scanner
5. **dirb** - Web content scanner
6. **searchsploit** - ExploitDB command-line search
7. **dig/host** - DNS enumeration tools
8. **whois** - Domain registration lookup

### Security Measures
- Non-root user execution (mcpuser)
- Input sanitization using regex
- Command timeouts to prevent hangs
- Output truncation to prevent memory exhaustion
- Capability-based permissions for network tools
- No arbitrary command execution (whitelist only in custom_command)

## Design Decisions

### Why FastMCP?
- Simpler than base MCP SDK
- Automatic tool registration
- Built-in stdio transport
- Easy decorator-based tool definition

### Why Single-line Docstrings?
- Multi-line docstrings cause gateway panic errors in Claude Desktop
- Single-line format is a technical requirement, not preference

### Why String Parameters?
- MCP protocol limitations with complex types
- Avoids Optional/Union type issues
- Empty string defaults work reliably
- Easy to validate with .strip()

### Why Long Timeouts?
- Security scans are inherently slow
- sqlmap can take 20+ minutes for thorough testing
- nmap intense scans can take 10+ minutes
- Better to wait than fail prematurely

## Tool Implementation Patterns

### Basic Tool Structure
```python
@mcp.tool()
async def tool_name(param: str = "") -> str:
    """Single-line description."""
    # 1. Validate input
    if not param.strip():
        return "❌ Error: ..."
    
    # 2. Sanitize input
    param = sanitize_input(param)
    
    # 3. Build command
    cmd = ["tool", param]
    
    # 4. Execute with timeout
    return run_command(cmd, timeout=300)
```

### Input Sanitization
- Regex-based: only allow safe characters
- Prevents command injection
- Allows necessary characters for IPs, URLs, paths

### Output Formatting
- Use emojis for visual parsing
- Truncate long outputs
- Include return codes
- Separate stdout/stderr

## Common Issues & Solutions

### Issue: Nmap "Operation not permitted"
**Solution**: Set capabilities in Dockerfile
```dockerfile
setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip /usr/bin/nmap
```

### Issue: WPScan rate limiting
**Solution**: Provide WPSCAN_API_TOKEN via Docker secrets
```bash
docker mcp secret set WPSCAN_API_TOKEN="your-token"
```

### Issue: SQLMap takes too long
**Solution**: Adjust timeout or use --level=1 --risk=1 for faster scans

### Issue: Output too large
**Solution**: Truncation at MAX_OUTPUT_LENGTH (default 10000 chars)

## Future Enhancements

Potential additions:
- Metasploit integration (complex, requires msfconsole)
- Burp Suite CLI integration
- Custom wordlist management
- Scan result parsing and formatting
- Report generation
- Integration with vulnerability databases
- Scan scheduling and queuing

## Best Practices for Users

1. **Always test in isolated environments**
2. **Start with basic scans before intense**
3. **Monitor resource usage** (scans can be CPU/network intensive)
4. **Save important outputs** (truncation may lose data)
5. **Use specific targets** (avoid /0 or large ranges)
6. **Combine tools** (use nmap first, then targeted scans)
7. **Review logs** (stderr has execution details)

## Maintenance Notes

- Update Kali base image regularly for latest tools
- Check tool versions: `docker run -it pentest-mcp-server bash`
- Monitor for deprecated tool options
- Test after FastMCP updates
- Verify capabilities after Docker updates

## References

- MCP Protocol: https://modelcontextprotocol.io
- FastMCP Documentation: https://github.com/jlowin/fastmcp
- Kali Linux: https://www.kali.org/docs/
- Individual tool documentation in /usr/share/doc/ within container