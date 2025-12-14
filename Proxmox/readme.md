# Proxmox MCP Server

A Model Context Protocol (MCP) server that integrates with your Proxmox Virtual Environment to manage virtual machines, containers, and infrastructure with enhanced flexibility through SSH fallbacks.

## Purpose

This MCP server provides a secure and robust interface for AI assistants to audit nodes, manage VM lifecycles, and provision new infrastructure directly from the chat interface. It intelligently switches between the QEMU Guest Agent and SSH for maximum reliability.

## Key Features

All tools are prefixed with `proxmox_` to ensure they are uniquely identifiable.

### Node & VM Management
- **`proxmox_list_nodes`**: Lists all physical nodes in the Proxmox cluster with status.
- **`proxmox_list_vms`**: Lists all QEMU VMs and LXC Containers on a specific node.
- **`proxmox_control_vm`**: Starts or stops a VM or Container (action: "start" or "stop").
- **`proxmox_create_vm_from_template`**: Creates a new VM by cloning an existing template.
- **`proxmox_delete_vm`**: Deletes a stopped VM or Container.
- **`proxmox_update_vm`**: Updates VM specs (cores, memory) and restarts it.
- **`proxmox_get_vm_stats`**: Get real-time statistics for a specific VM.
- **`proxmox_migrate_vm`**: Migrates a VM or Container to another node.

### LXC Containers
- **`proxmox_create_lxc`**: Creates a new LXC Container from a template.

### Snapshot & Backup Management
- **`proxmox_manage_snapshot`**: Manages VM snapshots (action: "create", "list", "rollback", "delete").
- **`proxmox_manage_backup`**: Manages VM backups (action: "create", "list", "restore").

### Firewall Management
- **`proxmox_add_firewall_rule`**: Adds a firewall rule to a VM.
- **`proxmox_list_firewall_rules`**: Lists firewall rules for a VM.
- **`proxmox_set_firewall`**: Enables or disables firewall for a VM (enable: true/false).

### System & Storage
- **`proxmox_list_storage`**: Lists storage usage on a specific node.
- **`proxmox_list_content`**: Lists ISOs and Container Templates on storage.
- **`proxmox_get_server_specs`**: Get detailed hardware specifications of a Proxmox server node (CPU, RAM, storage, network, uptime).

### Enhanced VM Interaction (Agent & SSH)

The following tools provide a hybrid approach for interacting with a VM's guest operating system. They will first attempt to use the **QEMU Guest Agent**. If the agent is not installed or unavailable, they will automatically **fall back to using SSH/SFTP**, providing a much more robust experience.

- **`proxmox_install_software`**: Installs software inside a VM.
- **`proxmox_execute_command`**: Executes an arbitrary shell command inside a VM.
- **`proxmox_read_file_vm`**: Reads a file from inside the VM. Uses SFTP for the SSH fallback.
- **`proxmox_write_file_vm`**: Writes a file inside the VM. Uses SFTP for the SSH fallback.

#### Using the SSH/SFTP Fallback
To use the fallback mechanism, you must provide the following **optional parameters** in your tool call, in addition to the standard ones (`node`, `vmid`, etc.):
- `ip_address`: The IP address of the virtual machine.
- `ssh_user`: The username for the SSH connection.
- `ssh_password` or `ssh_private_key`: The password or the raw private key string for authentication.
- `ssh_port`: (Optional) The SSH port, defaults to 22.

### Security (Firewall)
- **`proxmox_add_firewall_rule`**: Adds a firewall rule to a VM.
- **`proxmox_list_firewall_rules`**: Lists firewall rules for a VM.
- **`proxmox_set_firewall`**: Enables or disables firewall for a VM (enable: true/false).

## Timeouts for Reliability
To ensure the server remains responsive, the following timeouts are in place:
- **Proxmox API Calls**: 60-second read timeout.
- **SSH Connection**: 15-second connection timeout.
- **SSH Command Execution**:
    - `proxmox_install_software`: **5 minutes**.
    - `proxmox_execute_command`: **1 minute**.
- **QEMU Agent Commands**:
    - `proxmox_install_software`: **2 minutes**.
    - `proxmox_execute_command`: **1 minute**.

## Prerequisites

- Docker or another container runtime (for Docker deployment).
- **UVX** (for quick UVX deployment): Install from [Astral UV](https://github.com/astral-sh/uv).
- **Claude Desktop with Docker MCP Gateway support** (for on-demand container execution).
- A Proxmox VE server (v7.0+).
- Proxmox API credentials.
- **For VM guest operations**:
    1. **QEMU Guest Agent** (Recommended): Installed and running inside the target VM for best performance.
    2. **SSH Server**: As a fallback, an SSH server must be running in the VM, and you must have valid credentials.

## Deployment

Deployment can be done via **UVX** (recommended for quick testing), **Docker CLI** for local on-demand use, **Docker Compose** for a persistent remote service, or **Docker MCP Gateway** for on-demand container execution.

### Option 0: UVX (Quick Start - Recommended)

Perfect for development, testing, and quick deployment without Docker. Uses isolated Python environment.

1. **Install UV** (if not already installed):
   ```bash
   pip install uv
   ```

2. **Run with UVX**:
   ```bash
   # From the project directory
   PROXMOX_URL=https://your-proxmox-ip:8006 \
   PROXMOX_USER=root@pam \
   PROXMOX_PASSWORD=yourpassword \
   PROXMOX_VERIFY_SSL=false \
   uvx --from . proxmox-mcp
   ```

   **From any directory** (using absolute path):
   ```bash
   PROXMOX_URL=https://your-proxmox-ip:8006 \
   PROXMOX_USER=root@pam \
   PROXMOX_PASSWORD=yourpassword \
   PROXMOX_VERIFY_SSL=false \
   uvx --from /path/to/proxmox-project proxmox-mcp
   ```

   **Windows PowerShell**:
   ```powershell
   # From any directory
   $env:PROXMOX_URL="https://your-proxmox-ip:8006"
   $env:PROXMOX_USER="root@pam"
   $env:PROXMOX_PASSWORD="yourpassword"
   $env:PROXMOX_VERIFY_SSL="false"
   uvx --from "C:\Path\To\Proxmox\Project" proxmox-mcp
   ```

3. **Using .env file**:
   ```bash
   # Load environment variables from .env
   export $(cat .env | xargs) && uvx --from . proxmox-mcp
   ```

4. **Windows PowerShell**:
   ```powershell
   # Load .env and run
   Get-Content .env | ForEach-Object {
       if ($_ -match '^([^=]+)=(.*)$') {
           [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
       }
   }
   uvx --from . proxmox-mcp
   ```

**Benefits of UVX:**
- 🚀 **Fast Setup**: No Docker required
- 🔒 **Isolated**: Dependencies managed automatically
- 🛠️ **Development Friendly**: Easy to modify and test
- 📦 **Lightweight**: Only runs when needed

### Option 1: Docker CLI (Local - STDIO Transport)

Ideal for integration with local tools like Docker Desktop's MCP feature.

1.  **Build the Image**:
    ```bash
    docker-compose build
    # or
    docker build -t proxmox-mcp-server .
    ```

2.  **Run On-Demand via Docker CLI**:
    ```bash
    docker run -i --rm \
      -e PROXMOX_URL="https://192.168.1.10:8006" \
      -e PROXMOX_USER="root@pam" \
      -e PROXMOX_PASSWORD="yourpassword" \
      -e PROXMOX_VERIFY_SSL="false" \
      proxmox-mcp-server
    ```

### Option 2: Secure Remote Deployment (Docker Compose)

Recommended for deploying as a **persistent service** on a remote server. The included `docker-compose.yaml` uses **Caddy** as a reverse proxy for automatic HTTPS and Token Authentication.

1.  **Configure Environment**:
    Create a `.env` file on your remote machine:
    ```env
    # Proxmox Credentials
    PROXMOX_URL=https://your-proxmox-ip:8006
    PROXMOX_USER=root@pam
    PROXMOX_PASSWORD=yourpassword
    PROXMOX_VERIFY_SSL=false

    # MCP Security: Set a strong secret token
    MCP_AUTH_TOKEN=my-super-secret-token-123
    ```
    Also create a `PROXMOX_PASSWORD.txt` file with your password if you prefer using Docker secrets.

2.  **Build & Run**:
    ```bash
    docker-compose up --build -d
    ```
    - The server will be available at `https://your-server-ip:8443/`.

### Option 3: Secure On-Demand Deployment (SSH Gateway)

This method provides the best security and resource efficiency by running the container only when needed, tunneled through a standard SSH connection.

1.  **Server-Side Setup**:
    -   Install Docker.
    -   Build the image: `docker build -t proxmox-mcp-server .`
    -   Ensure your SSH server is running.

2.  **Client-Side Configuration**:
    For secure remote access via SSH tunnel, configure your MCP client with the following:

    ```json
    {
      "mcpServers": {
        "remote-proxmox-ssh": {
          "command": "ssh",
          "args": [
            "-i", "/path/to/your/private_ssh_key",
            "user@your-remote-server-ip",
            "docker", "run", "-i", "--rm", 
            "-e", "PROXMOX_URL=https://your-proxmox-ip:8006",
            "-e", "PROXMOX_USER=root@pam",
            "-e", "PROXMOX_PASSWORD=yourpassword",
            "proxmox-mcp-server:latest"
          ]
        }
      }
    }
    ```

### Option 4: Docker MCP Gateway (On-Demand Container)

**Recommended for Claude Desktop users** - Container only runs when tools are called, providing maximum resource efficiency and seamless integration.

1. **Build the Docker Image**:
   ```bash
   docker build -t proxmox-mcp-server .
   ```

2. **Configure Claude Desktop**:
   Use the configuration from `examples/claude-desktop-docker-gateway-example.json`:
   ```json
   {
     "mcpServers": {
       "proxmox": {
         "dockerImage": "proxmox-mcp-server",
         "env": {
           "PROXMOX_URL": "https://your-proxmox-ip:8006",
           "PROXMOX_USER": "root@pam",
           "PROXMOX_PASSWORD": "yourpassword",
           "PROXMOX_VERIFY_SSL": "false",
           "MCP_TRANSPORT": "sse"
         }
       }
     }
   }
   ```

   **Benefits of Docker MCP Gateway:**
   - 🚀 **On-Demand Execution**: Container starts only when you call a Proxmox tool
   - 💾 **Resource Efficient**: No persistent container running in background
   - 🔄 **Automatic Cleanup**: Container stops after tool execution completes
   - 🛡️ **Isolated**: Each tool call runs in a fresh container instance

### Option 5: Direct Install on Client using Repo

For direct installation and execution on your local client machine using the repository.

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/rezytijo/MCP-Collection.git
    cd MCP-Collection/Proxmox
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Client-Side Configuration**:
    Configure your MCP client to run the Python script directly. Below are examples for popular MCP-compatible tools.

    #### For Claude Desktop (Local Python Execution)
    Copy from `examples/claude-desktop-uvx-example.json` or create custom config:
    ```json
    {
      "mcpServers": {
        "Proxmox Test": {
          "command": "python",
          "args": [
            "path/to/proxmox_server.py"
          ],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "MCP_AUTH_TOKEN": "secret-token",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

    #### For Gemini (Google AI Studio or similar)
    In your Gemini MCP configuration, add a server entry with the Python command:
    ```json
    {
      "mcpServers": {
        "proxmox-gemini": {
          "command": "python",
          "args": ["path/to/proxmox_server.py"],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

    #### For GitHub Copilot
    Configure in your Copilot MCP settings:
    ```json
    {
      "mcpServers": {
        "proxmox-copilot": {
          "command": "python",
          "args": ["path/to/proxmox_server.py"],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

    #### For QWEN Desktop (Python)
    In QWEN Desktop's MCP server configuration:
    ```json
    {
      "mcpServers": {
        "proxmox-qwq": {
          "command": "python",
          "args": ["path/to/proxmox_server.py"],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

    #### For QWEN Desktop (UVX)
    In QWEN Desktop's MCP server configuration:
    ```json
    {
      "mcpServers": {
        "proxmox-qwq": {
          "command": "uvx",
          "args": ["--from", "/absolute/path/to/proxmox-project", "proxmox-mcp"],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

    Or copy from `examples/qwq-desktop-uvx-example.json`

    #### For LM Studio
    In LM Studio's MCP server configuration:
    ```json
    {
      "mcpServers": {
        "proxmox-lmstudio": {
          "command": "python",
          "args": ["path/to/proxmox_server.py"],
          "env": {
            "PROXMOX_URL": "https://your-proxmox-ip:8006",
            "PROXMOX_USER": "root@pam",
            "PROXMOX_PASSWORD": "yourpassword",
            "PROXMOX_VERIFY_SSL": "false"
          }
        }
      }
    }
    ```

## AI Client Configuration Files

Pre-configured JSON files are provided for easy integration with popular AI clients:

### Claude Desktop
- **`examples/claude-desktop-uvx-example.json`**: Configuration for UVX deployment (recommended)
- **`examples/claude-desktop-docker-example.json`**: Configuration for Docker CLI deployment
- **`examples/claude-desktop-docker-gateway-example.json`**: Configuration for Docker MCP Gateway (on-demand container execution)

**Usage:**
1. Copy the desired JSON file from `examples/` folder
2. Rename it to `claude_desktop_config.json`
3. Place it in Claude Desktop config directory
4. Restart Claude Desktop

### QWEN Desktop
- **`examples/qwq-desktop-uvx-example.json`**: Configuration for QWEN Desktop with UVX (recommended)
- **`examples/qwq-desktop-python-example.json`**: Configuration for QWEN Desktop with Python direct

**Usage:**
1. Copy the desired JSON file from `examples/` folder
2. Paste content to QWEN Desktop's MCP configuration
3. Update credentials with your actual Proxmox details
4. Restart QWEN Desktop

### LM Studio
- **`examples/lm-studio-mcp-example.json`**: Configuration for LM Studio MCP integration

**Usage:**
1. Copy the content from `examples/lm-studio-mcp-example.json`
2. Paste to LM Studio's MCP server configuration
3. Restart LM Studio

### VS Code
- **`examples/vscode-mcp-example.json`**: Configuration for VS Code MCP extension

**Usage:**
1. Copy the content from `examples/vscode-mcp-example.json`
2. Paste to your VS Code settings or MCP configuration
3. Restart VS Code

### Custom Configuration
All configuration files include:
- **Placeholder credentials**: Replace `your-proxmox-ip`, `yourpassword` with your actual Proxmox details
- SSL verification disabled (safe for self-signed certificates)
- STDIO transport for local communication

**Important**: Update the credentials in the JSON files in `examples/` folder before using them!

## License

MIT License