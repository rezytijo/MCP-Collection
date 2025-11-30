import os
from proxmoxer import ProxmoxAPI
import sys

PROXMOX_URL = os.environ.get("PROXMOX_URL")
PROXMOX_USER = os.environ.get("PROXMOX_USER")
PROXMOX_PASSWORD = os.environ.get("PROXMOX_PASSWORD")
PROXMOX_VERIFY_SSL = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"

if not all([PROXMOX_URL, PROXMOX_USER, PROXMOX_PASSWORD]):
    print("Error: Missing PROXMOX_URL, PROXMOX_USER, or PROXMOX_PASSWORD environment variables.")
    sys.exit(1)

try:
    host = PROXMOX_URL.replace("https://", "").replace("http://", "").split("/")[0]
    proxmox = ProxmoxAPI(
        host,
        user=PROXMOX_USER,
        password=PROXMOX_PASSWORD,
        verify_ssl=PROXMOX_VERIFY_SSL
    )
    nodes = proxmox.nodes.get()
    print("Successfully connected to Proxmox and listed nodes:")
    for node in nodes:
        print(f"- {node['node']} (Status: {node['status']})")
except Exception as e:
    print(f"Error connecting to Proxmox: {e}")
    sys.exit(1)
