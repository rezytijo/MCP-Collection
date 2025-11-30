# MCP-Collection: Multi-Architecture Containerized Micro-Control Panel Servers

This repository hosts a collection of Micro-Control Panel (MCP) servers, each designed for specific tasks (e.g., Proxmox management, Kali Linux pentesting tools). The project is structured as a monorepo, with each MCP server residing in its own subdirectory.

## Project Structure

-   `.github/workflows/`: Contains GitHub Actions for automated Docker image builds and pushes.
-   `Proxmox/`:
    -   `Dockerfile`: Defines the Docker image for the Proxmox MCP server.
    -   `proxmox_server.py`: The Python application for Proxmox management.
    -   `requirements.txt`: Python dependencies.
    -   `proxmox-mcp.yaml`: MCP server configuration.
    -   `Caddyfile`: Caddy server configuration for reverse proxy and authentication.
    -   `build_and_push.ps1`: (Legacy/local) PowerShell script to build and push Docker images.
    -   `docker-compose.yaml`: (Legacy/local) Docker Compose for local Proxmox server.
-   `Kali-Linux/`:
    -   `Dockerfile`: Defines the Docker image for the Kali Linux MCP server.
    -   `pentest_server.py`: The Python application for Kali Linux pentesting tools.
    -   `requirements.txt`: Python dependencies.
    -   `build_and_push.ps1`: (Legacy/local) PowerShell script to build and push Docker images.

## Getting Started

### Prerequisites

-   Docker Desktop or Docker Engine installed.
-   Git installed.
-   (Optional for local development) PowerShell for running `build_and_push.ps1` scripts.

### Clone the Repository

```bash
git clone https://github.com/rezytijo/MCP-Collection.git
cd MCP-Collection
```

### Automated Builds with GitHub Actions

This repository is configured with GitHub Actions to automatically build and push multi-architecture Docker images to Docker Hub whenever changes are pushed to the `main` branch within the `Proxmox/` or `Kali-Linux/` directories.

-   **Workflow File**: `.github/workflows/build-and-push.yml`
-   **Image Naming Convention**:
    -   `rezytijo/proxmox-mcp-server:<DATE>` and `rezytijo/proxmox-mcp-server:latest`
    -   `rezytijo/kali-mcp-server:<DATE>` and `rezytijo/kali-mcp-server:latest`
    Where `<DATE>` is in `dd-MM-yyyy` format.

**Note**: To enable the GitHub Actions, you need to configure `DOCKER_USERNAME` and `DOCKER_PASSWORD` as repository secrets in your GitHub repository settings.

### Running MCP Servers with Docker Compose (Local Development)

A `docker-compose.yaml` file is provided in the root of this repository to run both the Proxmox and Kali-Linux MCP servers together, exposed via a Caddy reverse proxy.

#### 1. Configure Caddy (for secure remote deployment)

The `Caddyfile` for the Proxmox MCP server (located in `Proxmox/Caddyfile`) can be adapted for the main reverse proxy if you wish to use Caddy with HTTPS and Bearer Token authentication. For local development, a simpler Caddy configuration might suffice or you can use the one provided.

#### 2. Create the main `docker-compose.yaml` (Example)

_This section will be populated with the actual `docker-compose.yaml` content in the next step._

### Usage

Once the services are running via Docker Compose, you can interact with them. For example, if using Caddy as a reverse proxy, you might access:

-   **Proxmox MCP Server**: `https://your-domain.com/proxmox` or `http://localhost:8000/proxmox`
-   **Kali-Linux MCP Server**: `https://your-domain.com/kali` or `http://localhost:8000/kali`

Remember to adjust `your-domain.com` and port mappings based on your `docker-compose.yaml` configuration.

## Contributing

Feel free to open issues or pull requests. Please ensure your changes adhere to the existing code style and conventions.
