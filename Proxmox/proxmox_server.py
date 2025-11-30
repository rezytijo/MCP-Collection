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
from proxmoxer import ProxmoxAPI
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
        # Add extra structured data if present
        if hasattr(record, "structured"):
            log_obj.update(record.structured)
            
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_obj)

# Get Log Level from Env
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
handler = logging.StreamHandler(sys.stderr)

if LOG_LEVEL == "DEBUG":
    handler.setFormatter(JSONFormatter())
else:
    # Simple 1-row format for INFO/WARN/ERROR
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(LOG_LEVEL)

# Create specific logger
logger = logging.getLogger("proxmox-mcp")
logger.setLevel(LOG_LEVEL)

# === DECORATORS ===

def log_activity(func):
    """Decorator to log tool execution, inputs (redacted), timing, and result status."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        
        # Redact sensitive arguments
        safe_kwargs = {}
        for k, v in kwargs.items():
            if k.lower() in ['password', 'secret', 'token']:
                safe_kwargs[k] = "***REDACTED***"
            else:
                safe_kwargs[k] = v

        logger.info(f"Tool Start: {tool_name}")
        logger.debug(f"Arguments: {safe_kwargs}", extra={"structured": {
            "event": "tool_start",
            "tool": tool_name,
            "arguments": safe_kwargs
        }})

        try:
            result = await func(*args, **kwargs)
            duration = round(time.time() - start_time, 4)
            
            if isinstance(result, str):
                if result.startswith("❌"):
                    status = "error"
                elif result.startswith("⚠️"):
                    status = "warning"
                else:
                    status = "success"
            else:
                status = "success"

            logger.info(f"Tool Finish: {tool_name} ({status}, {duration}s)")
            logger.debug(f"Result details for {tool_name}", extra={"structured": {
                "event": "tool_finish",
                "tool": tool_name,
                "duration_sec": duration,
                "status": status
            }})
            return result

        except Exception as e:
            duration = round(time.time() - start_time, 4)
            logger.error(f"Tool Crash: {tool_name} - {str(e)}")
            logger.debug("Crash details", exc_info=True, extra={"structured": {
                "event": "tool_crash",
                "tool": tool_name,
                "duration_sec": duration,
                "error": str(e)
            }})
            return f"❌ Internal Server Error in {tool_name}: {str(e)}"
            
    return wrapper

# === INITIALIZATION ===

# Initialize MCP server - NO PROMPT PARAMETER!
mcp = FastMCP("proxmox")

# Configuration
PROXMOX_URL = os.environ.get("PROXMOX_URL", "")
PROXMOX_USER = os.environ.get("PROXMOX_USER", "")
PROXMOX_PASSWORD = os.environ.get("PROXMOX_PASSWORD", "")
PROXMOX_VERIFY_SSL = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
MCP_TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio").lower()
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))

# === UTILITY FUNCTIONS ===

def get_proxmox_client():
    """Helper to authenticate and return the ProxmoxAPI client."""
    if not PROXMOX_URL or not PROXMOX_USER or not PROXMOX_PASSWORD:
        logger.error("Missing credentials")
        raise ValueError("Missing Proxmox credentials. Set PROXMOX_URL, PROXMOX_USER, and PROXMOX_PASSWORD.")
    
    host = PROXMOX_URL.replace("https://", "").replace("http://", "").split("/")[0]
    
    return ProxmoxAPI(
        host,
        user=PROXMOX_USER,
        password=PROXMOX_PASSWORD,
        verify_ssl=PROXMOX_VERIFY_SSL
    )

def generate_secure_password(length=12):
    """Generate a secure random password with mixed case, numbers, and punctuation."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in string.punctuation for c in password)):
            return password

def get_next_vmid(proxmox):
    """Helper to find the next available VMID starting from 100."""
    cluster_resources = proxmox.cluster.resources.get(type="vm")
    existing_ids = {int(res['vmid']) for res in cluster_resources if 'vmid' in res}
    candidate = 100
    while candidate in existing_ids:
        candidate += 1
    return str(candidate)

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
            status_emoji = "🟢" if node.get('status') == 'online' else "🔴"
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
async def proxmox_start_vm(node: str = "", vmid: str = "") -> str:
    """Start a specific VM or Container by ID on a Node."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required"
    
    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).status.start.post()
            return f"⚡ Signal sent to start VM {vmid} on {node}"
        except:
            try:
                proxmox.nodes(node).lxc(vmid).status.start.post()
                return f"⚡ Signal sent to start LXC {vmid} on {node}"
            except Exception as inner_e:
                 return f"❌ Error starting {vmid}: {str(inner_e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_stop_vm(node: str = "", vmid: str = "") -> str:
    """Stop (shutdown) a specific VM or Container by ID on a Node."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required"

    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).status.shutdown.post()
            return f"⚡ Signal sent to shutdown VM {vmid} on {node}"
        except:
            try:
                proxmox.nodes(node).lxc(vmid).status.shutdown.post()
                return f"⚡ Signal sent to shutdown LXC {vmid} on {node}"
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
async def proxmox_create_snapshot(node: str = "", vmid: str = "", name: str = "", description: str = "") -> str:
    """Create a snapshot of a VM."""
    if not node.strip() or not vmid.strip() or not name.strip():
        return "❌ Error: Node, VMID, and snapshot name are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        vm_res.snapshot.post(snapname=name, description=description)
        return f"📸 Snapshot '{name}' created for VM {vmid}."
    except Exception as e:
        return f"❌ Error creating snapshot: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_snapshots(node: str = "", vmid: str = "") -> str:
    """List all snapshots for a specific VM."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        snapshots = vm_res.snapshot.get()
        
        if not snapshots:
            return f"No snapshots found for VM {vmid}."
            
        output = [f"📸 Snapshots for VM {vmid}:"]
        for snap in snapshots:
            name = snap.get('name')
            if not name and snap.get('description') == "You are here!":
                 name = "(Current State)"
            ts = snap.get('snaptime', snap.get('time', 'Unknown'))
            desc = snap.get('description', 'No description')
            output.append(f"- {name}: {desc} (Time: {ts})")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error listing snapshots: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_rollback_snapshot(node: str = "", vmid: str = "", snapshot_name: str = "") -> str:
    """Rollback a VM to a specific snapshot."""
    if not node.strip() or not vmid.strip() or not snapshot_name.strip():
        return "❌ Error: Node, VMID, and snapshot name are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        vm_res.snapshot(snapshot_name).rollback.post()
        return f"↩️ VM {vmid} rollback to snapshot '{snapshot_name}' initiated."
    except Exception as e:
        return f"❌ Error rolling back snapshot: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_delete_snapshot(node: str = "", vmid: str = "", snapshot_name: str = "") -> str:
    """Delete a specific snapshot from a VM."""
    if not node.strip() or not vmid.strip() or not snapshot_name.strip():
        return "❌ Error: Node, VMID, and snapshot name are required."

    try:
        proxmox = get_proxmox_client()
        vm_res = proxmox.nodes(node).qemu(vmid)
        vm_res.snapshot(snapshot_name).delete()
        return f"🗑️ Snapshot '{snapshot_name}' deleted for VM {vmid}."
    except Exception as e:
        return f"❌ Error deleting snapshot: {str(e)}"

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
        content_items = proxmox.nodes(node).storage(storage).content.get()
        
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
        
        output = [f"📦 **Content on {storage} (Node: {node})**:\n"]
        
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
async def proxmox_install_software(node: str = "", vmid: str = "", software: str = "") -> str:
    """
    Install software inside a VM using QEMU Guest Agent.
    """
    if not node.strip() or not vmid.strip() or not software.strip():
        return "❌ Error: Node, VMID, and software name are required."

    software = software.lower()
    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).agent.get("info")
        except:
             return f"❌ Error: QEMU Guest Agent is not running on VM {vmid}. Ensure it is installed and the VM is running."

        commands = []
        if software == "docker":
            commands = ["/bin/bash", "-c", "curl -fsSL https://get.docker.com | sh"]
        elif software == "nginx":
            commands = ["/bin/bash", "-c", "apt-get update && apt-get install -y nginx"]
        elif software == "update":
            commands = ["/bin/bash", "-c", "apt-get update && apt-get upgrade -y"]
        elif software == "wordpress_docker":
             commands = ["/bin/bash", "-c", "docker run -d --name wordpress -p 80:80 -e WORDPRESS_DB_HOST=host.docker.internal -e WORDPRESS_DB_USER=root -e WORDPRESS_DB_PASSWORD=root wordpress"]
        else:
            return f"⚠️ Unknown software '{software}'. Supported: docker, nginx, update, wordpress_docker."

        res = proxmox.nodes(node).qemu(vmid).agent.exec.post(command=commands)
        pid = res.get('pid')
        
        if not pid:
            return "❌ Failed to start execution (No PID returned)."

        retries = 0
        max_retries = 60 
        while retries < max_retries:
            status = proxmox.nodes(node).qemu(vmid).agent('exec-status').get(pid=pid)
            if status.get('exited') == 1:
                exitcode = status.get('exitcode')
                out_data = status.get('out-data', '')
                err_data = status.get('err-data', '')
                if exitcode == 0:
                    return f"✅ '{software}' installed successfully!\nOutput: {out_data}"
                else:
                    return f"❌ Installation failed (Exit Code {exitcode}).\nError: {err_data}\nOutput: {out_data}"
            time.sleep(2)
            retries += 1

        return f"⏳ Installation of '{software}' started (PID {pid}), but timed out waiting for response. Check VM manually."

    except Exception as e:
        return f"❌ Error executing agent command: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_execute_command(node: str = "", vmid: str = "", command: str = "") -> str:
    """Execute an arbitrary shell command inside a VM using QEMU Guest Agent."""
    if not node.strip() or not vmid.strip() or not command.strip():
        return "❌ Error: Node, VMID, and command are required."

    try:
        proxmox = get_proxmox_client()
        try:
            proxmox.nodes(node).qemu(vmid).agent.get("info")
        except:
             return f"❌ Error: QEMU Guest Agent is not running on VM {vmid}."

        cmd_list = ["/bin/bash", "-c", command]
        res = proxmox.nodes(node).qemu(vmid).agent.exec.post(command=cmd_list)
        pid = res.get('pid')
        
        if not pid:
            return "❌ Failed to start execution (No PID returned)."

        retries = 0
        max_retries = 30 
        while retries < max_retries:
            status = proxmox.nodes(node).qemu(vmid).agent('exec-status').get(pid=pid)
            if status.get('exited') == 1:
                exitcode = status.get('exitcode')
                out_data = status.get('out-data', '')
                err_data = status.get('err-data', '')
                if exitcode == 0:
                    return f"✅ Command executed successfully.\nOutput: {out_data}"
                else:
                    return f"❌ Command failed (Exit Code {exitcode}).\nError: {err_data}\nOutput: {out_data}"
            time.sleep(1)
            retries += 1

        return f"⏳ Command started (PID {pid}), but waiting timed out."

    except Exception as e:
        return f"❌ Error executing command: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_create_backup(node: str = "", vmid: str = "", storage: str = "local", mode: str = "snapshot", compression: str = "zstd") -> str:
    """Trigger a backup (vzdump) for a specific VM or Container."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        res = proxmox.nodes(node).vzdump.post(
            vmid=vmid,
            storage=storage,
            mode=mode,
            compress=compression
        )
        upid = res
        return f"✅ Backup started for VM {vmid} (Task: {upid}). check Proxmox UI for progress."
    except Exception as e:
        return f"❌ Error starting backup: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_list_backups(node: str = "", storage: str = "") -> str:
    """List backup files on a specific node/storage."""
    if not node.strip() or not storage.strip():
        return "❌ Error: Node and Storage are required."

    try:
        proxmox = get_proxmox_client()
        contents = proxmox.nodes(node).storage(storage).content.get(content="backup")
        
        output = [f"📦 **Backups on {storage}**:"]
        for item in contents:
            volid = item.get('volid')
            size = int(item.get('size', 0) / 1024 / 1024) # MB
            vmid = item.get('vmid', 'unknown')
            output.append(f"- VM {vmid}: `{volid}` ({size}MB)")
            
        return "\n".join(output)
    except Exception as e:
        return f"❌ Error listing backups: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_restore_backup(node: str = "", vmid: str = "", backup_file: str = "", storage: str = "local-lvm") -> str:
    """Restore a VM from a backup file."""
    if not node.strip() or not backup_file.strip():
        return "❌ Error: Node and Backup File (volid) are required."

    try:
        proxmox = get_proxmox_client()
        
        if not vmid:
            vmid = get_next_vmid(proxmox)
        
        proxmox.nodes(node).qmrestore.post(vmid=vmid, archive=backup_file, storage=storage)
        
        return f"✅ Restore started for VM {vmid} from {backup_file}."
    except Exception as e:
        return f"❌ Error restoring backup: {str(e)}"

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
async def proxmox_read_file_vm(node: str = "", vmid: str = "", file_path: str = "") -> str:
    """Read text content from a specific path inside the VM via QEMU Guest Agent."""
    if not node.strip() or not vmid.strip() or not file_path.strip():
        return "❌ Error: Node, VMID, and File Path are required."

    try:
        proxmox = get_proxmox_client()
        res = proxmox.nodes(node).qemu(vmid).agent('file-read').get(file=file_path)
        
        content_b64 = res.get('content', '')
        content_bytes = base64.b64decode(content_b64)
        content_str = content_bytes.decode('utf-8', errors='replace')
        
        return f"📄 **File: {file_path}**\n```\n{content_str}\n```"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"

@mcp.tool()
@log_activity
async def proxmox_write_file_vm(node: str = "", vmid: str = "", file_path: str = "", content: str = "") -> str:
    """Write content to a path inside the VM via QEMU Guest Agent."""
    if not node.strip() or not vmid.strip() or not file_path.strip():
        return "❌ Error: Node, VMID, and File Path are required."

    try:
        proxmox = get_proxmox_client()
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
        
        proxmox.nodes(node).qemu(vmid).agent('file-write').post(
            file=file_path, 
            content=content_b64,
            encode=1
        )
        return f"✅ File '{file_path}' written successfully."
    except Exception as e:
        return f"❌ Error writing file: {str(e)}"

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
async def proxmox_get_vm_config(node: str = "", vmid: str = "") -> str:
    """Get the full configuration of a specific VM or Container."""
    if not node.strip() or not vmid.strip():
        return "❌ Error: Node and VMID are required."

    try:
        proxmox = get_proxmox_client()
        try:
            config = proxmox.nodes(node).qemu(vmid).config.get()
            vm_type = "VM"
        except:
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

if __name__ == "__main__":
    logger.info("Starting Proxmox MCP server...", extra={"structured": {"event": "startup"}})
    try:
        if MCP_TRANSPORT == "sse":
            logger.info(f"Starting MCP server with SSE transport on port {MCP_PORT}")
            mcp.run(transport='sse', port=MCP_PORT)
        else:
            logger.info("Starting MCP server with STDIO transport (default)")
            mcp.run(transport='stdio')
    except Exception as e:
        logger.fatal(f"Server failed to start: {e}", exc_info=True, extra={"structured": {"event": "fatal_crash"}})
        sys.exit(1)