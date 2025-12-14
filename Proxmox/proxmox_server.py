#!/usr/bin/env python3
"""
Proxmox MCP Server - Manage VMs and Nodes
"""
import os
import sys
import logging
import json
import secrets
import string
import base64
import time
import functools
import io
import paramiko
import asyncio
import shlex
import signal
from proxmoxer import ProxmoxAPI
from proxmoxer.core import ResourceException
from mcp.server.fastmcp import FastMCP

# === LOGGING CONFIGURATION ===

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging."""
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "structured"):
            log_obj.update(record.structured)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler(sys.stderr)

if LOG_LEVEL == "DEBUG":
    handler.setFormatter(JSONFormatter())
else:
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(LOG_LEVEL)
logger = logging.getLogger("proxmox-mcp")
logger.setLevel(LOG_LEVEL)

# === DECORATORS ===

def log_activity(func):
    """Decorator to log tool execution, inputs (redacted), timing, and result status."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        
        safe_kwargs = {k: ("***REDACTED***" if k.lower() in ['password', 'secret', 'token', 'ssh_password', 'ssh_private_key'] else v) for k, v in kwargs.items()}

        logger.info(f"Tool Start: {tool_name}")
        logger.debug(f"Arguments: {safe_kwargs}", extra={"structured": {"event": "tool_start", "tool": tool_name, "arguments": safe_kwargs}})

        try:
            result = await func(*args, **kwargs)
            duration = round(time.time() - start_time, 4)
            status = "success"
            if isinstance(result, str):
                if result.startswith("❌"): status = "error"
                elif result.startswith("⚠️"): status = "warning"
            
            logger.info(f"Tool Finish: {tool_name} ({status}, {duration}s)")
            logger.debug(f"Result details for {tool_name}", extra={"structured": {"event": "tool_finish", "tool": tool_name, "duration_sec": duration, "status": status}})
            return result

        except Exception as e:
            duration = round(time.time() - start_time, 4)
            logger.error(f"Tool Crash: {tool_name} - {str(e)}", exc_info=True)
            return f"❌ Internal Server Error in {tool_name}: {str(e)}"
            
    return wrapper

# === INITIALIZATION ===

PROXMOX_URL = os.environ.get("PROXMOX_URL", "")
PROXMOX_USER = os.environ.get("PROXMOX_USER", "")
PROXMOX_PASSWORD = os.environ.get("PROXMOX_PASSWORD", "")
if not PROXMOX_PASSWORD:
    secret_path = "/run/secrets/PROXMOX_PASSWORD"
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            PROXMOX_PASSWORD = f.read().strip()
PROXMOX_VERIFY_SSL = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio").lower()
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
mcp = FastMCP("proxmox", port=MCP_PORT, host='0.0.0.0')

# === UTILITY FUNCTIONS ===

def generate_secure_password(length=12):
    """Generate a secure random password with mixed case, numbers, and punctuation."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password) and any(c in string.punctuation for c in password)):
            return password

def get_next_vmid(proxmox):
    """Helper to find the next available VMID starting from 100."""
    cluster_resources = proxmox.cluster.resources.get(type="vm")
    existing_ids = {int(res['vmid']) for res in cluster_resources if 'vmid' in res}
    candidate = 100
    while candidate in existing_ids:
        candidate += 1
    return str(candidate)

def get_proxmox_client():
    """Helper to authenticate and return the ProxmoxAPI client."""
    password = PROXMOX_PASSWORD
    secret_path = "/run/secrets/proxmox_password"
    if os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            password = f.read().strip()
    if not all([PROXMOX_URL, PROXMOX_USER, password]):
        raise ValueError("Missing Proxmox credentials. Set PROXMOX_URL, PROXMOX_USER, and PROXMOX_PASSWORD.")
    host = PROXMOX_URL.replace("https://", "").replace("http://", "").split("/")[0]
    # Added timeout=(30, 60) for connect and read timeouts
    return ProxmoxAPI(host, user=PROXMOX_USER, password=password, verify_ssl=PROXMOX_VERIFY_SSL, timeout=(30, 60))

def _connect_ssh():
    """Returns an unconnected paramiko.SSHClient instance."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client

def _get_pkey(ssh_private_key):
    """Parses a private key string into a paramiko PKey object."""
    if not ssh_private_key:
        return None
    key_types = [paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey]
    for key_type in key_types:
        try:
            return key_type.from_private_key(io.StringIO(ssh_private_key))
        except paramiko.SSHException:
            continue
    raise ValueError("Invalid or unsupported private key format.")

def _execute_ssh_command(ip_address, ssh_user, ssh_password, ssh_private_key, ssh_port, command, cmd_timeout=60): # Added cmd_timeout parameter
    """Helper function to execute a command over SSH."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        pkey = None
        if ssh_private_key:
            pkey = _get_pkey(ssh_private_key)

        logger.debug(f"Connecting to {ssh_user}@{ip_address}:{ssh_port} via SSH")
        client.connect(
            hostname=ip_address,
            port=ssh_port,
            username=ssh_user,
            password=ssh_password,
            pkey=pkey,
            timeout=15 # SSH connection timeout
        )
        
        logger.debug(f"Executing SSH command: {command}")
        # Use cmd_timeout for command execution
        stdin, stdout, stderr = client.exec_command(command, timeout=cmd_timeout) 
        exit_code = stdout.channel.recv_exit_status()
        out_data = stdout.read().decode('utf-8', errors='replace')
        err_data = stderr.read().decode('utf-8', errors='replace')
        
        return exit_code, out_data, err_data
            
    except Exception as e:
        logger.error(f"SSH helper function failed: {e}", exc_info=True)
        return -1, "", str(e)
    finally:
        client.close()

def _read_sftp_file(client, file_path):
    """Reads a file via SFTP."""
    sftp = None
    try:
        sftp = client.open_sftp()
        with sftp.open(file_path, 'r') as f:
            content = f.read().decode('utf-8', errors='replace')
            return f"📄 **File: {file_path} (via SFTP)**\n```\n{content}\n```"
    except FileNotFoundError:
        return f"❌ SFTP read failed: File not found at '{file_path}'."
    except Exception as e:
        logger.error(f"SFTP read failed for {file_path}: {e}", exc_info=True)
        return f"❌ SFTP read failed: {str(e)}"
    finally:
        if sftp: sftp.close()

def _write_sftp_file(client, file_path, content):
    """Writes a file via SFTP."""
    sftp = None
    try:
        sftp = client.open_sftp()
        with sftp.open(file_path, 'w') as f:
            f.write(content)
        return f"✅ File '{file_path}' written successfully via SFTP."
    except Exception as e:
        logger.error(f"SFTP write failed for {file_path}: {e}", exc_info=True)
        return f"❌ SFTP write failed: {str(e)}"
    finally:
        if sftp: sftp.close()

# === MCP TOOLS ===

@mcp.tool()
@log_activity
async def proxmox_list_nodes() -> str:
    """List all nodes in the Proxmox cluster."""
    import socket
    try:
        host_str = PROXMOX_URL.replace("https://", "").replace("http://", "").split("/")[0]
        if ":" in host_str:
            h, p = host_str.split(":")
            p = int(p)
        else:
            h = host_str
            p = 8006
        
        logger.debug(f"Testing connection to {h}:{p}", extra={"structured": {"event": "conn_test"}})
        s = socket.create_connection((h, p), timeout=3)
        s.close()
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return f"❌ Network Error: Could not connect to {PROXMOX_URL} ({e})"

    try:
        proxmox = get_proxmox_client()
        nodes = proxmox.nodes.get()
        
        output = ["📊 Proxmox Nodes:"]
        for node in nodes:
            status_emoji = "ONLINE" if node.get('status') == 'online' else "OFFLINE"
            output.append(f"- {status_emoji} {node.get('node')} (CPU: {node.get('cpu', 0):.1%}, RAM: {int(node.get('mem', 0)/1024/1024)}MB)")
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"API Error: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_vms(node: str = "") -> str:
    """List all VMs and LXC containers on a specific node."""
    if not node.strip():
        return "❌ Error: Node name is required"
        
    try:
        proxmox = get_proxmox_client()
        
        qemu_vms = proxmox.nodes(node).qemu.get()
        lxc_cts = proxmox.nodes(node).lxc.get()
        
        output = [f"📊 VMs on node '{node}':"]
        
        if not qemu_vms and not lxc_cts:
            return f"⚠️ No VMs or Containers found on node '{node}'."

        for vm in qemu_vms:
            status = vm.get('status')
            icon = "🟢" if status == "running" else "🔴"
            output.append(f"{icon} [VM {vm.get('vmid')}] {vm.get('name')} - {status}")

        for ct in lxc_cts:
            status = ct.get('status')
            icon = "🟢" if status == "running" else "🔴"
            output.append(f"{icon} [LXC {ct.get('vmid')}] {ct.get('name')} - {status}")
            
        return "\n".join(output)
    except Exception as e:
        logger.error(f"API Error: {e}", exc_info=True)
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_control_vm(node: str = "", vmid: str = "", action: str = "") -> str:
    """Start or stop a specific VM or Container by ID on a Node."""
    if not node.strip() or not vmid.strip() or action not in ["start", "stop"]:
        return "❌ Error: Node, VMID, and action ('start' or 'stop') are required"
    
    try:
        proxmox = get_proxmox_client()
        if action == "start":
            try:
                proxmox.nodes(node).qemu(vmid).status.start.post()
                return f"⚡ Signal sent to start VM {vmid} on {node}"
            except:
                try:
                    proxmox.nodes(node).lxc(vmid).status.start.post()
                    return f"⚡ Signal sent to start LXC {vmid} on {node}"
                except Exception as inner_e:
                     return f"❌ Error starting {vmid}: {str(inner_e)}"
        elif action == "stop":
            try:
                proxmox.nodes(node).qemu(vmid).status.stop.post()
                return f"⚡ Signal sent to force stop VM {vmid} on {node}"
            except:
                try:
                    proxmox.nodes(node).lxc(vmid).status.stop.post()
                    return f"⚡ Signal sent to force stop LXC {vmid} on {node}"
                except Exception as inner_e:
                    return f"❌ Error stopping {vmid}: {str(inner_e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_create_vm_from_template(
    node: str = "", 
    vmid: str = "", 
    template_id: str = "", 
    name: str = "", 
    ip: str = "",
    cores: int = 0,
    memory: int = 0,
    disk_size: str = "64G",
    password: str = ""
) -> str:
    """
    Clone a template to create a new VM. 
    """
    if not node.strip() or not template_id.strip() or not name.strip():
        return "❌ Error: Node, template ID, and Name are required"

    if not password:
        password = generate_secure_password()
        pass_msg = f"🔑 **Generated Password**: `{password}`"
    else:
        pass_msg = "🔑 **Password**: (Set by user)"

    try:
        proxmox = get_proxmox_client()
        
        if not vmid:
            vmid = get_next_vmid(proxmox)
            logger.info(f"Auto-selected VMID: {vmid}")

        proxmox.nodes(node).qemu(template_id).clone.post(newid=vmid, name=name, full=1)
        
        config_updates = {}
        if cores > 0: config_updates['cores'] = cores
        if memory > 0: config_updates['memory'] = memory
        config_updates['cipassword'] = password

        if ip:
            if "/" not in ip: ip = f"{ip}/24"
            parts = ip.split(".")
            gw = f"{parts[0]}.{parts[1]}.{parts[2]}.1"
            config_updates['ipconfig0'] = f"ip={ip},gw={gw}"

        if config_updates:
            try:
                proxmox.nodes(node).qemu(vmid).config.post(**config_updates)
            except Exception as config_e:
                 logger.error(f"Config update failed: {config_e}")
                 return f"⚠️ VM {vmid} created but configuration failed: {config_e}\n{pass_msg}"

        resize_msg = ""
        if disk_size:
            try:
                vm_config = proxmox.nodes(node).qemu(vmid).config.get()
                target_disk = None
                for bus in ['scsi', 'virtio', 'sata', 'ide']:
                    for i in range(6):
                        d = f"{bus}{i}"
                        if d in vm_config:
                            target_disk = d
                            break
                    if target_disk: break
                
                if target_disk:
                    proxmox.nodes(node).qemu(vmid).resize.put(disk=target_disk, size=disk_size)
                    resize_msg = f", Disk: {disk_size}"
                else:
                    resize_msg = " (Disk resize skipped - no disk found)"

            except Exception as disk_e:
                logger.error(f"Disk resize failed: {disk_e}")
                resize_msg = f" (Disk resize failed: {disk_e})"

        return f"✅ VM {vmid} ('{name}') created from template {template_id} on {node}.\nSpecs: {cores if cores else 'Default'} Cores, {memory if memory else 'Default'}MB RAM{resize_msg}.\nIP: {ip if ip else 'Default'}.\n{pass_msg}"
    except Exception as e:
        return f"❌ Error cloning VM: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_delete_vm(node: str = "", vmid: str = "") -> str:
    """Delete a specific VM or Container (Must be stopped first)."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required"

    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).delete()
            return f"🗑️ VM {vmid} deleted successfully."
        except:
            try:
                proxmox.nodes(node).lxc(vmid).delete()
                return f"🗑️ LXC {vmid} deleted successfully."
            except Exception as inner_e:
                return f"❌ Error deleting {vmid}: {str(inner_e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_update_vm(node: str = "", vmid: str = "", cores: int = 0, memory: int = 0) -> str:
    """Update VM specs (cores, memory) and restart it."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required"
    
    if cores <= 0 and memory <= 0:
        return "⚠️ No changes requested. Provide 'cores' or 'memory' > 0."

    try:
        proxmox = get_proxmox_client()
        
        try:
            vm_res = proxmox.nodes(node).qemu(vmid)
            config = vm_res.config.get()
            status_info = vm_res.status.current.get()
            current_status = status_info.get('status')
            curr_cores = config.get('cores', 'unknown')
            curr_memory = config.get('memory', 'unknown')
        except Exception as e:
            return f"❌ Could not fetch VM {vmid} details: {e}"

        config_updates = {}
        changes_report = []
        
        if cores > 0: 
            config_updates['cores'] = cores
            changes_report.append(f"Cores: {curr_cores} -> {cores}")
        if memory > 0:
            config_updates['memory'] = memory
            changes_report.append(f"Memory: {curr_memory}MB -> {memory}MB")
            
        if not config_updates:
             return "⚠️ No effective changes to apply."

        vm_res.config.post(**config_updates)

        action_taken = ""
        try:
            if current_status == 'running':
                vm_res.status.reboot.post()
                action_taken = "Reboot Signal Sent 🔄"
            else:
                vm_res.status.start.post()
                action_taken = "VM Started 🟢"
        except Exception as boot_err:
            action_taken = f"⚠️ Restart failed: {boot_err}"

        return f"✅ VM {vmid} Updated.\n📊 Changes:\n" + "\n".join(f"- {c}" for c in changes_report) + f"\n\n⚡ Action: {action_taken}"

    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_manage_snapshot(node: str = "", vmid: str = "", action: str = "", name: str = "", description: str = "") -> str:
    """Manage snapshots for a VM: create, list, rollback, or delete."""
    if not node.strip() or not vmid.strip() or action not in ["create", "list", "rollback", "delete"]:
        return "❌ Error: Node, VMID, and action ('create', 'list', 'rollback', or 'delete') are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        
        if action == "create":
            if not name.strip():
                return "❌ Error: Snapshot name is required for create action."
            vm_res.snapshot.post(snapname=name, description=description)
            return f"📸 Snapshot '{name}' created for VM {vmid}."
        
        elif action == "list":
            snapshots = vm_res.snapshot.get()
            if not snapshots:
                return f"No snapshots found for VM {vmid}."
            output = [f"📸 Snapshots for VM {vmid}:"]
            for snap in snapshots:
                snap_name = snap.get('name')
                if not snap_name and snap.get('description') == "You are here!":
                     snap_name = "(Current State)"
                ts = snap.get('snaptime', snap.get('time', 'Unknown'))
                desc = snap.get('description', 'No description')
                output.append(f"- {snap_name}: {desc} (Time: {ts})")
            return "\n".join(output)
        
        elif action == "rollback":
            if not name.strip():
                return "❌ Error: Snapshot name is required for rollback action."
            vm_res.snapshot(name).rollback.post()
            return f"↩️ VM {vmid} rollback to snapshot '{name}' initiated."
        
        elif action == "delete":
            if not name.strip():
                return "❌ Error: Snapshot name is required for delete action."
            vm_res.snapshot(name).delete()
            return f"🗑️ Snapshot '{name}' deleted for VM {vmid}."
    
    except Exception as e:
        return f"❌ Error managing snapshot ({action}): {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_get_vm_stats(node: str = "", vmid: str = "") -> str:
    """Get real-time statistics (CPU, RAM, Disk) for a specific VM."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."
        
    try:
        proxmox = get_proxmox_client()
        status = proxmox.nodes(node).qemu(vmid).status.current.get()
        
        state = status.get('status', 'unknown')
        uptime = int(status.get('uptime', 0))
        cpu_usage = status.get('cpu', 0) * 100
        mem_used = int(status.get('mem', 0) / 1024 / 1024)
        mem_total = int(status.get('maxmem', 0) / 1024 / 1024)
        mem_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0
        
        uptime_str = f"{uptime // 3600}h {(uptime % 3600) // 60}m"
        icon = "🟢" if state == 'running' else "🔴"
        
        return (
            f"📊 **VM {vmid} Stats** {icon}\n"
            f"State: {state.upper()}\n"
            f"Uptime: {uptime_str}\n"
            f"CPU Load: {cpu_usage:.1f}%\n"
            f"RAM Usage: {mem_used}MB / {mem_total}MB ({mem_percent:.1f}%)"
        )
    except Exception as e:
        return f"❌ Error getting stats: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_storage(node: str = "") -> str:
    """List storage usage on a specific node."""
    if not node.strip():
        return "❌ Error: Node is required."
        
    try:
        proxmox = get_proxmox_client()
        storages = proxmox.nodes(node).storage.get()
        
        output = [f"💾 **Storage on {node}**:"]
        for st in storages:
            name = st.get('storage')
            total = int(st.get('total', 0) / 1024 / 1024 / 1024)
            used = int(st.get('used', 0) / 1024 / 1024 / 1024)
            percent = (used / total * 100) if total > 0 else 0
            active = "🟢" if st.get('active') else "🔴"
            output.append(f"- {active} **{name}**: {used}GB / {total}GB ({percent:.1f}%) - {st.get('type')})")
            
        return "\n".join(output)
    except Exception as e:
         return f"❌ Error listing storage: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_content(node: str = "", storage: str = "") -> str:
    """List ISOs and Container Templates on a specific storage."""
    if not node.strip() or not storage.strip():
        return "❌ Error: Node and Storage are required."

    try:
        proxmox = get_proxmox_client()
        content_items = proxmox.nodes(node).storage(storage).content.get(content="iso,vztmpl")
        
        isos = []
        templates = []

        for item in content_items:
            content_type = item.get('content')
            volid = item.get('volid') # e.g., local:iso/ubuntu-22.04.3-live-server-amd64.iso
            name = volid.split('/')[-1] # Extract filename

            if content_type == "iso":
                isos.append(name)
            elif content_type == "vztmpl": # LXC Container Template
                templates.append(name)
        
        output = [f"📦 **Content on {storage} (Node: {node})**\n"]
        
        if isos:
            output.append("💿 **ISOs**:")
            for iso in isos:
                output.append(f"- {iso}")
        else:
            output.append("💿 No ISOs found.")
        
        if templates:
            output.append("\n📚 **Container Templates (LXC)**:")
            for tmpl in templates:
                output.append(f"- {tmpl}")
        else:
            output.append("\n📚 No Container Templates found.")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error listing content: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_install_software(
    node: str = "", 
    vmid: str = "", 
    software: str = "",
    ip_address: str = "",
    ssh_user: str = "",
    ssh_password: str = "",
    ssh_private_key: str = "",
    ssh_port: int = 22
) -> str:
    """
    Install software inside a VM using QEMU Guest Agent or fallback to SSH.
    For SSH, you must provide ip_address, ssh_user, and either ssh_password or ssh_private_key.
    """
    if not all([node, vmid, software]):
        return "❌ Error: Node, VMID, and software name are required."

    proxmox = get_proxmox_client()
    
    # 1. Try QEMU Guest Agent first
    try:
        logger.info(f"Attempting to use QEMU Guest Agent for VM {vmid}.")
        proxmox.nodes(node).qemu(vmid).agent.get("info")
        
        install_command = (
            f"sh -c 'if command -v apt-get >/dev/null; then "
            f"apt-get update && apt-get install -y {software}; "
            f"elif command -v yum >/dev/null; then "
            f"yum install -y {software}; "
            f"elif command -v dnf >/dev/null; then "
            f"dnf install -y {software}; "
            f"else echo \"Unsupported package manager.\" >&2; exit 1; fi'"
        )

        cmd_list = ["/bin/bash", "-c", install_command]
        res = proxmox.nodes(node).qemu(vmid).agent.exec.post(command=cmd_list)
        pid = res.get('pid')
        
        if not pid:
            raise ResourceException("Failed to start execution (No PID returned).")

        for _ in range(60): # 2-minute timeout
            status = proxmox.nodes(node).qemu(vmid).agent('exec-status').get(pid=pid)
            if status.get('exited') == 1:
                exitcode = status.get('exitcode')
                out_data = status.get('out-data', '')
                err_data = status.get('err-data', '')
                if exitcode == 0:
                    return f"✅ '{software}' installed successfully via Guest Agent!\nOutput: {out_data}"
                else:
                    return f"❌ Agent command failed (Exit Code {exitcode}).\nError: {err_data}\nOutput: {out_data}"
            time.sleep(2)
        
        return f"⏳ Agent command for '{software}' started (PID {pid}), but timed out. Check VM manually."

    except ResourceException as e:
        logger.warning(f"QEMU Guest Agent failed for VM {vmid}: {e}. Attempting SSH fallback.")

        if not all([ip_address, ssh_user]) or not (ssh_password or ssh_private_key):
            return (f"❌ QEMU Guest Agent not available on VM {vmid}.\n"
                    f"⚠️ To use SSH fallback, provide: 'ip_address', 'ssh_user', and either 'ssh_password' or 'ssh_private_key'.")

        logger.info(f"Using SSH fallback for VM {vmid} at {ip_address}.")
        
        install_command = (
            f"if command -v apt-get >/dev/null; then "
            f"sudo apt-get update && sudo apt-get install -y {software}; "
            f"elif command -v yum >/dev/null; then "
            f"sudo yum install -y {software}; "
            f"elif command -v dnf >/dev/null; then "
            f"sudo dnf install -y {software}; "
            f"else echo \"Unsupported package manager.\" >&2; exit 1; fi"
        )
        
        # Use a 5-minute timeout for installation commands via SSH
        exit_code, out_data, err_data = await asyncio.get_event_loop().run_in_executor(
            None, _execute_ssh_command, ip_address, ssh_user, ssh_password, ssh_private_key, ssh_port, install_command, 300
        )

        if exit_code == 0:
            return f"✅ '{software}' installed successfully via SSH!\nOutput: {out_data}"
        else:
            return f"❌ SSH command failed (Exit Code {exit_code}).\nError: {err_data}\nOutput: {out_data}"

@mcp.tool()
@log_activity
async def proxmox_execute_command(
    node: str = "", 
    vmid: str = "", 
    command: str = "",
    ip_address: str = "",
    ssh_user: str = "",
    ssh_password: str = "",
    ssh_private_key: str = "",
    ssh_port: int = 22
) -> str:
    """Execute a shell command in a VM via QEMU Guest Agent or SSH fallback."""
    if not all([node, vmid, command]):
        return "❌ Error: Node, VMID, and command are required."

    proxmox = get_proxmox_client()
    
    try:
        logger.info(f"Attempting to use QEMU Guest Agent for command on VM {vmid}.")
        proxmox.nodes(node).qemu(vmid).agent.get("info")

        cmd_list = ["/bin/bash", "-c", command]
        res = proxmox.nodes(node).qemu(vmid).agent.exec.post(command=cmd_list)
        pid = res.get('pid')
        
        if not pid:
            raise ResourceException("Failed to start execution (No PID returned).")

        for _ in range(30): # 1-minute timeout (agent)
            status = proxmox.nodes(node).qemu(vmid).agent('exec-status').get(pid=pid)
            if status.get('exited') == 1:
                exitcode = status.get('exitcode')
                out_data = status.get('out-data', '')
                err_data = status.get('err-data', '')
                if exitcode == 0:
                    return f"✅ Agent command executed successfully.\nOutput: {out_data}"
                else:
                    return f"❌ Agent command failed (Exit Code {exitcode}).\nError: {err_data}\nOutput: {out_data}"
            time.sleep(2)

        return f"⏳ Agent command started (PID {pid}), but timed out."

    except ResourceException as e:
        logger.warning(f"QEMU Guest Agent failed for VM {vmid}: {e}. Attempting SSH fallback.")
        
        if not all([ip_address, ssh_user]) or not (ssh_password or ssh_private_key):
            return (f"❌ QEMU Guest Agent not available on VM {vmid}.\n"
                    f"⚠️ To use SSH fallback, provide: 'ip_address', 'ssh_user', and either 'ssh_password' or 'ssh_private_key'.")

        logger.info(f"Using SSH fallback for command on VM {vmid} at {ip_address}.")
        
        # Use a 1-minute timeout for arbitrary commands via SSH
        exit_code, out_data, err_data = await asyncio.get_event_loop().run_in_executor(
            None, _execute_ssh_command, ip_address, ssh_user, ssh_password, ssh_private_key, ssh_port, command, 60
        )
        
        if exit_code == 0:
            return f"✅ Command executed successfully via SSH.\nOutput: {out_data}"
        else:
            return f"❌ SSH command failed (Exit Code {exit_code}).\nError: {err_data}\nOutput: {out_data}"

@mcp.tool()
@log_activity
async def proxmox_read_file_vm(
    node: str = "", 
    vmid: str = "", 
    file_path: str = "",
    ip_address: str = "",
    ssh_user: str = "",
    ssh_password: str = "",
    ssh_private_key: str = "",
    ssh_port: int = 22
) -> str:
    """Read file content from a VM using QEMU Guest Agent or fallback to SSH."""
    if not all([node, vmid, file_path]):
        return "❌ Error: Node, VMID, and File Path are required."

    proxmox = get_proxmox_client()
    try:
        logger.info(f"Attempting to read file via Guest Agent from VM {vmid}.")
        res = proxmox.nodes(node).qemu(vmid).agent('file-read').get(file=file_path)
        content_b64 = res.get('content', '')
        content_bytes = base64.b64decode(content_b64)
        content_str = content_bytes.decode('utf-8', errors='replace')
        return f"📄 **File: {file_path} (via Agent)**\n```\n{content_str}\n```"

    except ResourceException as e:
        logger.warning(f"QEMU Guest Agent failed for VM {vmid}: {e}. Attempting SSH fallback.")
        
        if not all([ip_address, ssh_user]) or not (ssh_password or ssh_private_key):
            return (f"❌ QEMU Guest Agent not available on VM {vmid}.\n"
                    f"⚠️ To use SSH fallback, provide: 'ip_address', 'ssh_user', and either 'ssh_password' or 'ssh_private_key'.")

        logger.info(f"Using SSH fallback to read file on VM {vmid} at {ip_address}.")
        
        client = _connect_ssh()
        try:
            pkey = _get_pkey(ssh_private_key)
            client.connect(hostname=ip_address, port=ssh_port, username=ssh_user, password=ssh_password, pkey=pkey, timeout=15)
            # SFTP read operations do not have explicit per-operation timeouts beyond connection
            result = await asyncio.get_event_loop().run_in_executor(None, _read_sftp_file, client, file_path)
            return result
        except Exception as ssh_e:
            return f"❌ SSH/SFTP connection failed: {ssh_e}"
        finally:
            client.close()

@mcp.tool()
@log_activity
async def proxmox_write_file_vm(
    node: str = "", 
    vmid: str = "", 
    file_path: str = "", 
    content: str = "",
    ip_address: str = "",
    ssh_user: str = "",
    ssh_password: str = "",
    ssh_private_key: str = "",
    ssh_port: int = 22
) -> str:
    """Write content to a file in a VM using QEMU Guest Agent or fallback to SSH."""
    if not all([node, vmid, file_path]):
        return "❌ Error: Node, VMID, and File Path are required."

    proxmox = get_proxmox_client()
    try:
        logger.info(f"Attempting to write file via Guest Agent to VM {vmid}.")
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        proxmox.nodes(node).qemu(vmid).agent('file-write').post(
            file=file_path, 
            content=content_b64,
            encode=1
        )
        return f"✅ File '{file_path}' written successfully via Guest Agent."

    except ResourceException as e:
        logger.warning(f"QEMU Guest Agent failed for VM {vmid}: {e}. Attempting SSH fallback.")
        
        if not all([ip_address, ssh_user]) or not (ssh_password or ssh_private_key):
            return (f"❌ QEMU Guest Agent not available on VM {vmid}.\n"
                    f"⚠️ To use SSH fallback, provide: 'ip_address', 'ssh_user', and either 'ssh_password' or 'ssh_private_key'.")

        logger.info(f"Using SSH fallback to write file on VM {vmid} at {ip_address}.")
        
        client = _connect_ssh()
        try:
            pkey = _get_pkey(ssh_private_key)
            client.connect(hostname=ip_address, port=ssh_port, username=ssh_user, password=ssh_password, pkey=pkey, timeout=15)
            # SFTP write operations do not have explicit per-operation timeouts beyond connection
            result = await asyncio.get_event_loop().run_in_executor(None, _write_sftp_file, client, file_path, content)
            return result
        except Exception as ssh_e:
            return f"❌ SSH/SFTP connection failed: {ssh_e}"
        finally:
            client.close()

@mcp.tool()
@log_activity
async def proxmox_manage_backup(node: str = "", vmid: str = "", action: str = "", storage: str = "", backup_file: str = "", mode: str = "snapshot", compression: str = "zstd") -> str:
    """Manage backups for VMs: create, list, or restore."""
    if not node.strip() or action not in ["create", "list", "restore"]:
        return "❌ Error: Node and action ('create', 'list', or 'restore') are required."

    try:
        proxmox = get_proxmox_client()
        
        if action == "create":
            if not vmid.strip():
                return "❌ Error: VMID is required for create action."
            res = proxmox.nodes(node).vzdump.post(
                vmid=vmid,
                storage=storage or "local",
                mode=mode,
                compress=compression
            )
            upid = res
            return f"✅ Backup started for VM {vmid} (Task: {upid}). Check Proxmox UI for progress."
        
        elif action == "list":
            if not storage.strip():
                return "❌ Error: Storage is required for list action."
            contents = proxmox.nodes(node).storage(storage).content.get(content="backup")
            output = [f"📦 **Backups on {storage}**:"]
            for item in contents:
                volid = item.get('volid')
                size = int(item.get('size', 0) / 1024 / 1024) # MB
                vm_id = item.get('vmid', 'unknown')
                output.append(f"- VM {vm_id}: `{volid}` ({size}MB)")
            return "\n".join(output)
        
        elif action == "restore":
            if not backup_file.strip():
                return "❌ Error: Backup file (volid) is required for restore action."
            if not vmid.strip():
                vmid = get_next_vmid(proxmox)
            proxmox.nodes(node).qmrestore.post(vmid=vmid, archive=backup_file, storage=storage or "local-lvm")
            return f"✅ Restore started for VM {vmid} from {backup_file}."
    
    except Exception as e:
        return f"❌ Error managing backup ({action}): {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_migrate_vm(node: str = "", vmid: str = "", target_node: str = "", online: bool = True) -> str:
    """Migrate a VM/CT to another node."""
    if not node.strip() or not vmid.strip() or not target_node.strip():
        return "❌ Error: Source Node, VMID, and Target Node are required."
    
    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).migrate.post(target=target_node, online=int(online))
            return f"🚀 Migration started: VM {vmid} -> {target_node}"
        except:
            try:
                proxmox.nodes(node).lxc(vmid).migrate.post(target=target_node, restart=int(online))
                return f"🚀 Migration started: LXC {vmid} -> {target_node}"
            except Exception as inner_e:
                 return f"❌ Error migrating {vmid}: {str(inner_e)}"
    except Exception as e:
         return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_create_lxc(
    node: str = "", 
    vmid: str = "", 
    hostname: str = "", 
    password: str = "",
    ostemplate: str = "", 
    cores: int = 1, 
    memory: int = 512, 
    storage: str = "local-lvm",
    disk_size: str = "8G",
    net0: str = "name=eth0,bridge=vmbr0,ip=dhcp"
) -> str:
    """Create a new LXC Container."""
    if not node.strip() or not hostname.strip() or not ostemplate.strip():
        return "❌ Error: Node, Hostname, and OS Template are required."

    if not password:
        password = generate_secure_password()
        pass_msg = f"🔑 **Generated Password**: `{password}`"
    else:
        pass_msg = "🔑 **Password**: (Set by user)"

    try:
        proxmox = get_proxmox_client()
        if not vmid:
            vmid = get_next_vmid(proxmox)

        proxmox.nodes(node).lxc.post(
            vmid=vmid,
            hostname=hostname,
            password=password,
            ostemplate=ostemplate,
            cores=cores,
            memory=memory,
            storage=storage,
            rootfs=f"volume={disk_size}",
            net0=net0
        )
        return f"✅ LXC {vmid} ('{hostname}') created.\n{pass_msg}"
    except Exception as e:
        return f"❌ Error creating LXC: {str(e)}"


@mcp.tool()
@log_activity
async def proxmox_add_firewall_rule(
    node: str = "", 
    vmid: str = "", 
    type: str = "in", 
    action: str = "ACCEPT", 
    proto: str = "tcp",
    dport: str = "", 
    sport: str = "",
    comment: str = ""
) -> str:
    """Add a firewall rule to a VM."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        proxmox.nodes(node).qemu(vmid).firewall.rules.post(
            type=type,
            action=action,
            proto=proto,
            dport=dport,
            sport=sport,
            comment=comment,
            enable=1
        )
        return f"🛡️ Firewall rule added to VM {vmid}: {type} {action} {proto} dport:{dport}"
    except Exception as e:
        return f"❌ Error adding firewall rule: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_firewall_rules(node: str = "", vmid: str = "") -> str:
    """List firewall rules for a VM."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        rules = proxmox.nodes(node).qemu(vmid).firewall.rules.get()
        
        output = [f"🛡️ **Firewall Rules for VM {vmid}**:"]
        for r in rules:
            pos = r.get('pos')
            action = r.get('action')
            typ = r.get('type')
            proto = r.get('proto', 'any')
            dport = r.get('dport', '-')
            comment = r.get('comment', '')
            enable = "✅" if r.get('enable') else "🚫"
            output.append(f"{enable} [{pos}] {typ} {action} {proto} port:{dport} ({comment})")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error listing rules: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_set_firewall(node: str = "", vmid: str = "", enable: bool = True) -> str:
    """Enable or disable firewall for a VM."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        vm_res.config.post(firewall=int(enable))
        if enable:
            return f"🛡️ Firewall enabled for VM {vmid}."
        else:
            return f"🚫 Firewall disabled for VM {vmid}."
    except Exception as e:
        return f"❌ Error {'enabling' if enable else 'disabling'} firewall: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_test_connection() -> str:
    """Test connection to the Proxmox server."""
    try:
        proxmox = get_proxmox_client()
        # Test connection by getting version info
        version = proxmox.version.get()
        version_str = version.get('version', 'Unknown')
        release = version.get('release', 'Unknown')
        return f"✅ Connection successful!\n📊 Proxmox Version: {version_str}\n📅 Release: {release}"
    except Exception as e:
        return f"❌ Connection failed: {str(e)}\n🔍 Check PROXMOX_URL, credentials, and network connectivity."

@mcp.tool()
@log_activity
async def proxmox_get_vm_config(node: str = "", vmid: str = "") -> str:
    """Get the full configuration of a specific VM or Container."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        try:
            config = proxmox.nodes(node).qemu(vmid).config.get()
            vm_type = "VM"
        except Exception: # Catch generic exception as ProxmoxResourceError is not specific for qemu/lxc check
            try:
                config = proxmox.nodes(node).lxc(vmid).config.get()
                vm_type = "LXC"
            except Exception as inner_e:
                return f"❌ Error getting config for {vmid}: {str(inner_e)}"

        output = [f"⚙️ **Configuration for {vm_type} {vmid}**:"]
        for key, value in sorted(config.items()):
            output.append(f"- **{key}**: `{value}`")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error getting config: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_get_task_status(node: str = "", upid: str = "") -> str:
    """Get the status and logs of a background task (e.g., backup, restore, clone)."""
    if not node.strip() or not upid.strip():
        return "❌ Error: Node and UPID are required."

    try:
        proxmox = get_proxmox_client()
        status = proxmox.nodes(node).tasks(upid).status.get()
        
        exit_status = status.get('exitstatus', 'Running')
        start_time = status.get('starttime', 0)
        
        # Get Task Log
        log_entries = proxmox.nodes(node).tasks(upid).log.get()
        logs = "\n".join([l.get('t', '') for l in log_entries])
        
        icon = "🟢" if exit_status == "OK" else "🔴" if exit_status != "Running" else "⏳"
        
        return (
            f"📋 **Task Status: {upid}** {icon}\n"
            f"**Status**: {exit_status}\n"
            f"**Start Time**: {time.ctime(int(start_time))}\n\n"
            f"📜 **Log Output**:\n"
            f"```\n{logs}\n```"
        )
    except Exception as e:
        return f"❌ Error getting task status: {str(e)}"

@mcp.tool()
def proxmox_get_server_specs(node: str = "") -> str:
    """Get detailed hardware specifications of a Proxmox server node."""
    if not node.strip():
        return "Error: Node name is required."

    try:
        # Simple test first
        proxmox = get_proxmox_client()
        version = proxmox.version.get()
        ver = version.get('version', 'Unknown')

        # Get basic node info
        node_status = proxmox.nodes(node).status.get()
        cpu_info = node_status.get('cpuinfo', {})
        cpu_model = cpu_info.get('model', 'Unknown')
        cpu_cores = cpu_info.get('cores', 0)

        memory_info = node_status.get('memory', {})
        memory_total = int(memory_info.get('total', 0) / 1024 / 1024 / 1024)
        memory_used = int(memory_info.get('used', 0) / 1024 / 1024 / 1024)

        # Simple output - avoid any complex formatting
        result = "SERVER SPECIFICATIONS - Node: " + node + "\n"
        result += "=" * 50 + "\n"
        result += "Proxmox Version: " + ver + "\n\n"
        result += "CPU Information:\n"
        result += "- Model: " + cpu_model + "\n"
        result += "- Cores: " + str(cpu_cores) + "\n\n"
        result += "Memory (RAM):\n"
        result += "- Total: " + str(memory_total) + " GB\n"
        result += "- Used: " + str(memory_used) + " GB\n\n"
        result += "=" * 50

        return result

    except Exception as e:
        return "Error getting server specifications: " + str(e)


def main():
    """Main entry point for the Proxmox MCP server."""
    def signal_handler(signum, frame):
        logger.info(f"Server shutdown requested by signal {signum}", extra={"structured": {"event": "shutdown", "reason": f"signal_{signum}"}})
        print(f"\n🛑 Server stopped by signal {signum}.")
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except ValueError:
        # SIGTERM not available on Windows
        pass

    logger.info("Starting Proxmox MCP server...", extra={"structured": {"event": "startup"}})
    try:
        if MCP_TRANSPORT == "sse":
            logger.info(f"Starting MCP server with SSE transport on port {MCP_PORT}")
            mcp.run(transport='sse')
        else:
            logger.info("Starting MCP server with STDIO transport")
            mcp.run(transport='stdio')
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user (Ctrl+C)", extra={"structured": {"event": "shutdown", "reason": "keyboard_interrupt"}})
        print("\n🛑 Server stopped by user.")
    except Exception as e:
        logger.fatal(f"Server failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()