# MCP Proxmox Configuration Examples

This folder contains example configuration files for integrating MCP Proxmox with various AI desktop applications.

## Available Configurations

### Claude Desktop
- **`claude-desktop-uvx-example.json`** - Recommended configuration using UVX
- **`claude-desktop-docker-example.json`** - Alternative configuration using Docker CLI
- **`claude-desktop-docker-gateway-example.json`** - On-demand Docker MCP Gateway (container runs only when needed)

### QWEN Desktop
- **`qwq-desktop-uvx-example.json`** - Recommended configuration using UVX
- **`qwq-desktop-python-example.json`** - Alternative configuration using direct Python

### LM Studio
- **`lm-studio-mcp-example.json`** - Configuration for LM Studio MCP integration

### VS Code
- **`vscode-mcp-example.json`** - Configuration for VS Code MCP extension

## How to Use

1. **Choose your AI client** from the list above
2. **Copy the appropriate JSON file** to your clipboard
3. **Update the credentials** in the JSON:
   - Replace `your-proxmox-ip` with your actual Proxmox server IP
   - Replace `yourpassword` with your actual Proxmox password
4. **Configure your AI client** according to its documentation
5. **Restart the AI client** to apply changes

## Important Notes

- These are **example configurations** - you MUST update the credentials before use
- SSL verification is disabled by default (safe for self-signed certificates)
- For UVX configurations, ensure UV is installed: `pip install uv`
- For Docker configurations, ensure Docker is running
- **Docker MCP Gateway**: The `claude-desktop-docker-gateway-example.json` uses Claude Desktop's Docker MCP Gateway feature, where the container only runs when tools are called, providing better resource efficiency

## Environment Variables Required

All configurations require these environment variables to be set:

- `PROXMOX_URL` - Your Proxmox server URL (e.g., https://192.168.1.100:8006)
- `PROXMOX_USER` - Your Proxmox username (usually root@pam)
- `PROXMOX_PASSWORD` - Your Proxmox password
- `PROXMOX_VERIFY_SSL` - Set to "false" for self-signed certificates

## Testing

After configuration, test the connection by asking your AI assistant to run:
- `proxmox_test_connection` - Verify Proxmox API connectivity
- `proxmox_list_nodes` - List available Proxmox nodes