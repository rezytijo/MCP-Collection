# Proxmox MCP Server

A Model Context Protocol (MCP) server that integrates with your Proxmox Virtual Environment to manage virtual machines and containers.

## Purpose

This MCP server provides a secure interface for AI assistants to audit nodes, manage VM lifecycles, and provision new infrastructure directly from the chat interface.

## Features

All tools are prefixed with `proxmox_` to ensure they are uniquely identifiable.

### Node & VM Management
- **`proxmox_list_nodes`** - Lists all physical nodes in the Proxmox cluster with status.
- **`proxmox_list_vms`** - Lists all QEMU VMs and LXC Containers on a specific node.
- **`proxmox_start_vm`** - Sends a start signal to a VM or Container.
- **`proxmox_stop_vm`** - Sends a shutdown signal to a VM or Container.
- **`proxmox_create_vm_from_template`** - Creates a new VM by cloning an existing template.
    - **Auto-VMID**: Automatically finds the next free ID.
    - **Disk Resizing**: Auto-expands the primary disk (default 64G).
    - **Secure Passwords**: Auto-generates secure credentials if not provided.
    - **Network**: Configures Static IP/Gateway via Cloud-Init.
- **`proxmox_delete_vm`** - Deletes a stopped VM or Container.
- **`proxmox_update_vm`** - Update VM specs (cores, memory) and restart it.
- **`proxmox_get_vm_stats`** - Get real-time statistics (CPU, RAM, Disk) for a specific VM.
- **`proxmox_migrate_vm`** - Migrate a VM or Container to another node in the cluster.

### LXC Containers
- **`proxmox_create_lxc`** - Create a new LXC Container from a template.

### Snapshot & Backup Management
- **`proxmox_create_snapshot`** - Create a VM snapshot.
- **`proxmox_list_snapshots`** - List all snapshots for a specific VM.
- **`proxmox_rollback_snapshot`** - Rollback a VM to a specific snapshot.
- **`proxmox_delete_snapshot`** - Delete a specific snapshot from a VM.
- **`proxmox_create_backup`** - Trigger a `vzdump` backup for a VM/CT.
- **`proxmox_list_backups`** - List available backup files on storage.
- **`proxmox_restore_backup`** - Restore a VM from a backup file.

### System & Storage
- **`proxmox_list_storage`** - List storage usage on a specific node.
- **`proxmox_list_content`** - List ISOs and Container Templates on a specific storage.

### Guest Agent Integration (QEMU)
- **`proxmox_install_software`** - Install software inside a VM using QEMU Guest Agent. Supported: 'docker', 'nginx', 'update'.
- **`proxmox_execute_command`** - Execute an arbitrary shell command inside a VM.
- **`proxmox_read_file_vm`** - Read a file from inside the VM.
- **`proxmox_write_file_vm`** - Write a file inside the VM.

### Security (Firewall)
- **`proxmox_add_firewall_rule`** - Add a firewall rule to a VM.
- **`proxmox_list_firewall_rules`** - List firewall rules for a VM.

## Prerequisites

- Docker Desktop with MCP Toolkit enabled (for local deployment)
- Docker MCP CLI plugin (`docker mcp` command)
- A Proxmox VE server (v7.0+)
- Proxmox API Token or User Credentials
- **Note:** `install_software`, `execute_command`, and file operations require QEMU Guest Agent to be installed and running inside the target VM.

## Deployment

The server supports various deployment methods, balancing persistence, security, and resource usage.

### Option 1: Docker CLI (Local - STDIO Transport)

This is suitable for local development and direct integration with Docker Desktop's MCP feature. The container only runs when called by Docker Desktop's MCP client.

1. **Build the Image**:
   ```bash
   docker build -t proxmox-mcp-server .
   ```

2. **Run the Container (Interactive)**:
   Since this server communicates via Stdin/Stdout, you run it interactively (`-i`).
   ```bash
   docker run -i --rm \
     -e PROXMOX_URL="https://192.168.1.10:8006" \
     -e PROXMOX_USER="root@pam" \
     -e PROXMOX_PASSWORD="yourpassword" \
     -e PROXMOX_VERIFY_SSL="false" \
     proxmox-mcp-server
   ```

### Option 2: Secure Remote Deployment (Caddy Gateway + SSE)

The recommended way to deploy this on a remote server (e.g., a VM or a VPS) as a **persistent service** is using **Docker Compose** with **Caddy** as a reverse proxy. This provides HTTPS (automatically) and Token Authentication.

1. **Configure Environment**:
   Create a `.env` file in the root directory (on your remote machine):
   ```env
   # Proxmox Credentials
   PROXMOX_URL=https://192.168.1.10:8006
   PROXMOX_USER=root@pam
   PROXMOX_PASSWORD=yourpassword
   PROXMOX_VERIFY_SSL=false

   # MCP Security
   # Set this to a strong secret token!
   # Clients must send: Authorization: Bearer <this_token>
   MCP_AUTH_TOKEN=my-super-secret-token-123

   # Optional: Set LOG_LEVEL=DEBUG for JSON-formatted logs
   # LOG_LEVEL=DEBUG 
   ```

2. **Place `Caddyfile`**:
   Ensure the `Caddyfile` (provided in this project) is in the same directory as your `docker-compose.yaml`.

3. **Build & Run**:
   ```bash
   docker-compose up --build -d
   ```
   
   - The server will be available at `https://your-server-ip:8443/`.
   - If you configure Caddy with a real domain, it will automatically provision a valid Let's Encrypt certificate. For testing on `localhost` or via IP, Caddy will use self-signed certificates (which clients might warn about).

### Option 3: Secure On-Demand Deployment (SSH Gateway + STDIO) - Recommended for Zero Idle Resources

This method offers the best balance of security and resource efficiency for remote servers. The MCP server container only runs when an MCP client session is active, and communication is secured via SSH.

1.  **Server Side (Remote Machine Setup)**:
    *   Ensure Docker is installed.
    *   Ensure you have an SSH server running and configured for key-based authentication.
    *   **Build the Docker Image**:
        ```bash
        docker build -t proxmox-mcp-server .
        ```
    *   No need to run any containers persistently. The client will launch it on demand.

2.  **Client Side (Your Local Machine Configuration)**:
    *   **Install OpenSSH client**: Make sure `ssh` command is available in your PATH.
    *   **Generate an SSH key pair**: If you don't have one, `ssh-keygen`.
    *   **Copy public key to remote server**: Use `ssh-copy-id user@your-remote-server-ip` or manually add it to `~/.ssh/authorized_keys` on the remote server.
    *   **Configure your MCP Client (e.g., `claude_desktop_config.json`)**:

        ```json
        {
          "mcpServers": {
            "remote-proxmox-ssh": {
              "command": "ssh",
              "args": [
                "-i", "/path/to/your/private_ssh_key",  // Path to your local SSH private key
                "user@your-remote-server-ip",          // User and IP of your remote server
                "docker", "run", "-i", "--rm", 
                "-e", "PROXMOX_URL=https://192.168.1.10:8006", // Your Proxmox API URL
                "-e", "PROXMOX_USER=root@pam",                 // Your Proxmox User
                "-e", "PROXMOX_PASSWORD=yourpassword",         // Your Proxmox Password
                "-e", "PROXMOX_VERIFY_SSL=false",              // SSL verification
                "proxmox-mcp-server:latest"                    // The Docker image to run
              ]
            }
          }
        }
        ```
        *Note: Remember to replace placeholders like `/path/to/your/private_ssh_key`, `user@your-remote-server-ip`, and Proxmox credentials.*

    **Benefits of SSH Gateway**:
    *   **On-Demand**: The Docker container only starts when the MCP client needs it.
    *   **Zero Idle Resources**: No container or web server running 24/7 on your remote machine if not in use.
    *   **Highly Secure**: Leverages established SSH authentication and encryption.
    *   **No Port Exposure**: Only requires SSH access to the remote machine (typically port 22), avoiding exposure of custom HTTP ports.

## Installation (MCP Client)

### Docker Desktop MCP (Local)

To register this server with Docker Desktop's MCP feature:

1. **Import Catalog**:
   ```bash
   # Windows
   copy "proxmox-mcp.yaml" "%USERPROFILE%\.docker\mcp\catalogs\proxmox-mcp.yaml"
   ```
   *(Note: This uses `stdio` transport, suitable for local development with Docker Desktop.)*

2. **Set Secrets**:
   ```bash
   docker mcp secret set proxmox-url="https://..."
   docker mcp secret set proxmox-user="root@pam"
   docker mcp secret set proxmox-password="secret"
   ```

3. **Update Registry**:
   Ensure `proxmox` is listed in your `registry.yaml`.

### General MCP Client (Remote/SSE)

For MCP clients that support HTTP-based servers (like Claude Desktop, or custom integrations), you can configure it to point to the SSE endpoint from Option 2.

**Connection Configuration:**
```json
{
  "mcpServers": {
    "proxmox": {
      "url": "https://your-server-ip:8443/",
      "headers": {
        "Authorization": "Bearer my-super-secret-token-123"
      }
    }
  }
}
```
*Note: Ensure your MCP client supports custom HTTP headers for authentication.*

## Logging

You can configure the logging verbosity using the `LOG_LEVEL` environment variable.

- **`INFO` (Default)**: Simple, human-readable 1-row log format.
- **`DEBUG`**: Structured JSON logging with detailed request/response tracing.

## Architecture

**Secure On-Demand Deployment (SSH Gateway):**
```
MCP Client (Claude/Other)
    ↓ (SSH Tunnel)
[ Remote SSH Server ] → (Launches Docker Container)
    ↓ (STDIO)
[ Proxmox MCP Server (Container - on-demand) ]
    ↓ (HTTPS)
[ Proxmox API ]
```

## Development

### Local Testing (STDIO)

```bash
# Set environment variables for testing
export PROXMOX_URL="https://192.168.1.100:8006"
export PROXMOX_USER="root@pam"
export PROXMOX_PASSWORD="yourpassword"
export PROXMOX_VERIFY_SSL="false"
# Keep MCP_TRANSPORT unset or set to stdio for local testing
unset MCP_TRANSPORT 

# Run directly
python proxmox_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python proxmox_server.py
```

### Local Testing (SSE)

```bash
# Set environment variables for testing
export PROXMOX_URL="https://192.168.1.100:8006"
export PROXMOX_USER="root@pam"
export PROXMOX_PASSWORD="yourpassword"
export PROXMOX_VERIFY_SSL="false"
export MCP_TRANSPORT="sse" # Enable SSE transport
export MCP_PORT="8000"     # Specify port

# Run directly
python proxmox_server.py
# Server will listen on http://localhost:8000/
```

## License

MIT License
