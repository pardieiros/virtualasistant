# Jarvas Terminal API

Secure HTTP API service for executing whitelisted terminal commands on Proxmox host. Designed for integration with the Jarvas virtual assistant.

## Features

- ✅ Whitelist-based command validation
- ✅ Bearer token authentication
- ✅ Command timeout protection (20s default)
- ✅ Comprehensive logging
- ✅ Systemd service integration
- ✅ Safe command parsing (no shell injection)

## Security

**⚠️ IMPORTANT SECURITY CONSIDERATIONS:**

1. **Whitelist Protection**: Only explicitly whitelisted commands can be executed. This prevents arbitrary command execution.

2. **No Shell Injection**: Commands are parsed using `shlex.split()` and executed with `shell=False`, preventing shell injection attacks.

3. **Token Authentication**: All requests require a valid Bearer token in the Authorization header.

4. **Network Security**: 
   - **DO NOT** expose this API to the public internet
   - Only expose on local network (LAN) or via VPN (e.g., WireGuard)
   - Consider using a reverse proxy (nginx) with SSL/TLS

5. **Token Security**:
   - Use a strong, randomly generated token
   - Store the token securely (environment variable or .env file)
   - Never commit the token to version control
   - Rotate the token periodically

6. **File Permissions**: Ensure the service runs with appropriate permissions and the token file is readable only by the service user.

## Installation

### 1. Create Directory Structure

```bash
sudo mkdir -p /opt/jarvas-terminal/logs
cd /opt/jarvas-terminal
```

### 2. Copy Files

Copy the following files to `/opt/jarvas-terminal/`:
- `jarvas_terminal_api.py`
- `requirements.txt`
- `.env.example`

### 3. Create Virtual Environment

```bash
cd /opt/jarvas-terminal
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set a strong token
nano .env

# Generate a strong random token (optional, but recommended)
openssl rand -hex 32
```

Edit `.env` and set:
- `JARVAS_TERMINAL_TOKEN` - A strong random token
- `JARVAS_TERMINAL_PORT` - Port to listen on (default: 8900)
- Other settings as needed

### 5. Set Permissions

```bash
# Make script executable
chmod +x /opt/jarvas-terminal/jarvas_terminal_api.py

# Secure .env file
chmod 600 /opt/jarvas-terminal/.env

# Set ownership (adjust user/group as needed)
chown -R root:root /opt/jarvas-terminal
```

### 6. Install Systemd Service

```bash
# Copy service file
sudo cp jarvas-terminal.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable jarvas-terminal.service

# Start the service
sudo systemctl start jarvas-terminal.service

# Check status
sudo systemctl status jarvas-terminal.service
```

### 7. Verify Installation

```bash
# Check logs
sudo journalctl -u jarvas-terminal.service -f

# Or check the log file
tail -f /opt/jarvas-terminal/logs/jarvas_terminal.log
```

## Usage

### API Endpoint

**POST** `/api/system/terminal/run/`

**Headers:**
```
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json
```

**Request Body:**
```json
{
  "command": "docker ps"
}
```

**Response:**
```json
{
  "allowed": true,
  "command": ["docker", "ps"],
  "returncode": 0,
  "stdout": "CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS   PORTS   NAMES\n...",
  "stderr": "",
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

### Example Requests

#### Check Docker Containers

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker ps"}'
```

#### View Container Logs

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker logs --tail 50 searxng"}'
```

#### Restart Container

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "docker restart searxng"}'
```

#### List LXC Containers

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct list"}'
```

#### Check LXC Status

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "pct status 102"}'
```

#### Check Disk Usage

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "df -h"}'
```

#### Check Memory Usage

```bash
curl -X POST http://localhost:8900/api/system/terminal/run/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"command": "free -m"}'
```

## Whitelisted Commands

The following commands are whitelisted:

### Docker Commands
- `docker ps`
- `docker ps -a`
- `docker logs --tail N <container_name>`
- `docker logs -n N <container_name>`
- `docker restart <container_name>`

### Proxmox LXC Commands (pct)
- `pct list`
- `pct status <ID>`
- `pct start <ID>`
- `pct stop <ID>`

### Proxmox VM Commands (qm)
- `qm list`
- `qm status <ID>`
- `qm start <ID>`
- `qm stop <ID>`

### System Commands
- `df -h`
- `free -m` (or `free -g`, `free -h`)
- `uptime`

## Adding New Commands

To add new commands to the whitelist, edit `jarvas_terminal_api.py` and update the `COMMAND_WHITELIST` dictionary:

```python
COMMAND_WHITELIST: Dict[str, Dict] = {
    "newcommand": {
        "allowed_subcommands": ["sub1", "sub2"],
        "allowed_flags": ["--flag1", "-f"],
        "allow_any_args": False,
    },
    # ... existing commands
}
```

After modifying, restart the service:
```bash
sudo systemctl restart jarvas-terminal.service
```

## Troubleshooting

### Service Won't Start

1. Check logs:
   ```bash
   sudo journalctl -u jarvas-terminal.service -n 50
   ```

2. Verify Python and dependencies:
   ```bash
   /opt/jarvas-terminal/venv/bin/python3 --version
   /opt/jarvas-terminal/venv/bin/pip list
   ```

3. Check file permissions:
   ```bash
   ls -la /opt/jarvas-terminal/
   ```

### Commands Not Working

1. Verify command is in whitelist
2. Check command syntax matches whitelist exactly
3. Review logs for validation errors
4. Test command manually in terminal first

### Authentication Errors

1. Verify token in `.env` file matches the one in the request
2. Check token is not expired or changed
3. Ensure `Authorization: Bearer <TOKEN>` header is correct

## Service Management

```bash
# Start service
sudo systemctl start jarvas-terminal.service

# Stop service
sudo systemctl stop jarvas-terminal.service

# Restart service
sudo systemctl restart jarvas-terminal.service

# Check status
sudo systemctl status jarvas-terminal.service

# View logs
sudo journalctl -u jarvas-terminal.service -f

# Disable auto-start on boot
sudo systemctl disable jarvas-terminal.service
```

## Integration with Jarvas

To integrate with Jarvas, you'll need to:

1. Add a new service in the Jarvas backend that calls this API
2. Configure the API endpoint and token in Jarvas settings
3. Add appropriate tools/functions for the LLM to use

Example integration code (for Jarvas backend):

```python
import requests

def execute_proxmox_command(command: str) -> dict:
    """Execute a command on the Proxmox host via Terminal API."""
    url = "http://proxmox-host-ip:8900/api/system/terminal/run/"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"command": command}
    
    response = requests.post(url, json=data, headers=headers, timeout=25)
    response.raise_for_status()
    return response.json()
```

## License

This project is part of the Jarvas virtual assistant system.









