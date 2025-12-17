#!/usr/bin/env python3
"""
Jarvas Terminal API Service
Executes whitelisted terminal commands via HTTP API for Proxmox host management.
"""

import os
import re
import shlex
import subprocess
import logging
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Depends, Header
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from pydantic import BaseModel
    from dotenv import load_dotenv
except ImportError as e:
    print(f"ERROR: Missing required dependency: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables from .env file if it exists
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Server configuration
HOST = "0.0.0.0"
PORT = int(os.getenv("JARVAS_TERMINAL_PORT", "8900"))

# Authentication token (can be set via environment variable or .env file)
API_TOKEN = os.getenv("JARVAS_TERMINAL_TOKEN", "CHANGE_THIS_TOKEN_IN_PRODUCTION")

# Command execution timeout (seconds)
COMMAND_TIMEOUT = int(os.getenv("JARVAS_TERMINAL_TIMEOUT", "20"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/opt/jarvas-terminal/logs/jarvas_terminal.log")

# ============================================================================
# COMMAND WHITELIST
# ============================================================================

# Whitelist structure:
# {
#   "binary": {
#     "allowed_subcommands": ["subcommand1", "subcommand2", ...],
#     "allowed_flags": ["--flag1", "-f", ...],
#     "allow_any_args": False,  # If True, allows any arguments after validation
#   }
# }

COMMAND_WHITELIST: Dict[str, Dict] = {
    "docker": {
        "allowed_subcommands": ["ps", "logs", "restart"],
        "allowed_flags": ["-a", "--all", "--tail", "-n"],
        "allow_any_args": False,  # Container names are validated separately
    },
    "pct": {
        "allowed_subcommands": ["list", "status", "start", "stop", "exec"],
        "allowed_flags": [],
        "allow_any_args": False,  # LXC IDs are validated
    },
    "qm": {
        "allowed_subcommands": ["list", "status", "start", "stop"],
        "allowed_flags": [],
        "allow_any_args": False,  # VM IDs are validated
    },
    "df": {
        "allowed_subcommands": [],
        "allowed_flags": ["-h", "--human-readable"],
        "allow_any_args": False,
    },
    "free": {
        "allowed_subcommands": [],
        "allowed_flags": ["-m", "-g", "-h", "--mega", "--giga", "--human"],
        "allow_any_args": False,
    },
    "uptime": {
        "allowed_subcommands": [],
        "allowed_flags": [],
        "allow_any_args": False,
    },
}

# Allowed container/VM/LXC name patterns (for docker logs, restart, etc.)
# This is a simple validation - you can make it more strict if needed
ALLOWED_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"
ALLOWED_ID_PATTERN = r"^\d+$"  # For LXC/VM IDs

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging to both file and stdout."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Jarvas Terminal API",
    description="Secure terminal command execution API for Proxmox host management",
    version="1.0.0",
)

security = HTTPBearer()

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_command(command_str: str) -> Tuple[bool, List[str], str]:
    """
    Validate command against whitelist.
    
    Returns:
        Tuple of (is_allowed, parsed_command_list, error_message)
    """
    try:
        # Parse command using shlex to safely split arguments
        parsed = shlex.split(command_str)
        
        if not parsed:
            return False, [], "Empty command"
        
        binary = parsed[0]
        
        # Check if binary is in whitelist
        if binary not in COMMAND_WHITELIST:
            logger.warning(f"Command binary '{binary}' not in whitelist")
            return False, [], f"Binary '{binary}' is not allowed"
        
        whitelist_config = COMMAND_WHITELIST[binary]
        
        # Special validation for pct exec (MUST be before generic flag validation)
        # This prevents "--" from being treated as an invalid flag
        if binary == "pct" and len(parsed) >= 2 and parsed[1] == "exec":
            # Validate pct exec structure: pct exec <LXC_ID> -- docker ps [-a]
            if len(parsed) < 6:
                logger.warning(f"Invalid 'pct exec' command structure: {command_str}")
                return False, [], "Invalid 'pct exec' command structure. Expected: 'pct exec <LXC_ID> -- docker ps [-a]'"
            
            # Validate LXC ID (parsed[2])
            lxc_id = parsed[2]
            if not re.match(ALLOWED_ID_PATTERN, lxc_id):
                logger.warning(f"Invalid LXC ID in 'pct exec': {lxc_id}")
                return False, [], f"Invalid LXC ID format: {lxc_id}"
            
            # Validate separator "--" (parsed[3])
            if parsed[3] != "--":
                logger.warning(f"Missing '--' separator in 'pct exec': {command_str}")
                return False, [], "Missing '--' separator in 'pct exec' command"
            
            # Validate docker command (parsed[4] and parsed[5])
            if parsed[4] != "docker":
                logger.warning(f"Only 'docker' is allowed inside 'pct exec': {command_str}")
                return False, [], "Only 'docker' is allowed inside 'pct exec'"
            
            if parsed[5] != "ps":
                logger.warning(f"Only 'docker ps' is allowed inside 'pct exec': {command_str}")
                return False, [], "Only 'docker ps' or 'docker ps -a' is allowed inside 'pct exec'"
            
            # Validate optional -a flag (parsed[6] if exists)
            if len(parsed) == 7:
                if parsed[6] != "-a":
                    logger.warning(f"Invalid argument in 'pct exec': {parsed[6]}")
                    return False, [], "Only 'docker ps' or 'docker ps -a' is allowed inside 'pct exec'"
            elif len(parsed) > 7:
                logger.warning(f"Too many arguments in 'pct exec': {command_str}")
                return False, [], "Only 'docker ps' or 'docker ps -a' is allowed inside 'pct exec'"
            
            # pct exec validation passed - return immediately
            logger.info(f"pct exec command validated: {command_str}")
            return True, parsed, ""
        
        # Check subcommand if present (for non-pct-exec commands)
        if len(parsed) > 1:
            subcommand = parsed[1]
            
            # Check if it's a flag (starts with -)
            if subcommand.startswith("-"):
                # It's a flag, validate it
                if subcommand not in whitelist_config["allowed_flags"]:
                    logger.warning(f"Flag '{subcommand}' not allowed for '{binary}'")
                    return False, [], f"Flag '{subcommand}' is not allowed for '{binary}'"
            else:
                # It's a subcommand, validate it
                if subcommand not in whitelist_config["allowed_subcommands"]:
                    logger.warning(f"Subcommand '{subcommand}' not allowed for '{binary}'")
                    return False, [], f"Subcommand '{subcommand}' is not allowed for '{binary}'"
        
        # Validate flags in the command
        # Flags that take values: --tail, -n (for docker logs)
        flags_with_values = {"--tail", "-n"}
        i = 1
        while i < len(parsed):
            arg = parsed[i]
            if arg.startswith("-"):
                # Validate the flag
                if arg not in whitelist_config["allowed_flags"]:
                    logger.warning(f"Flag '{arg}' not allowed for '{binary}'")
                    return False, [], f"Flag '{arg}' is not allowed for '{binary}'"
                
                # If flag takes a value, validate the next argument is a number
                if arg in flags_with_values:
                    if i + 1 < len(parsed):
                        next_arg = parsed[i + 1]
                        if not next_arg.isdigit():
                            return False, [], f"Flag '{arg}' requires a numeric value"
                        i += 2  # Skip flag and its value
                        continue
            i += 1
        
        # Special validation for docker logs and restart
        if binary == "docker":
            if len(parsed) >= 2:
                subcommand = parsed[1]
                if subcommand in ["logs", "restart"]:
                    # For logs and restart, we need a container name
                    # Find the container name (the last non-flag, non-flag-value argument)
                    flags_with_values = {"--tail", "-n"}
                    container_name = None
                    i = len(parsed) - 1
                    skip_next = False
                    
                    while i >= 2:  # Start from end, skip binary and subcommand
                        arg = parsed[i]
                        if skip_next:
                            skip_next = False
                            i -= 1
                            continue
                        
                        if arg.startswith("-"):
                            # If this flag takes a value, skip the previous arg (which is the value)
                            if arg in flags_with_values:
                                skip_next = True
                        else:
                            # This is a potential container name
                            container_name = arg
                            break
                        i -= 1
                    
                    if not container_name:
                        return False, [], "Container name required for 'docker logs' or 'docker restart'"
                    
                    # Basic validation: alphanumeric, underscore, hyphen
                    if not re.match(ALLOWED_NAME_PATTERN, container_name):
                        return False, [], f"Invalid container name format: {container_name}"
        
        # Special validation for pct and qm commands (status, start, stop)
        if binary in ["pct", "qm"]:
            if len(parsed) >= 2:
                subcommand = parsed[1]
                # Skip validation for exec (already handled above)
                if subcommand in ["status", "start", "stop"]:
                    # Need an ID
                    if len(parsed) < 3:
                        return False, [], f"ID required for 'pct/qm {subcommand}'"
                    
                    id_arg = parsed[2]
                    if not re.match(ALLOWED_ID_PATTERN, id_arg):
                        return False, [], f"Invalid ID format: {id_arg}"
        
        # Command is valid
        logger.info(f"Command validated successfully: {command_str}")
        return True, parsed, ""
    
    except ValueError as e:
        logger.error(f"Error parsing command '{command_str}': {e}")
        return False, [], f"Invalid command syntax: {e}"
    except Exception as e:
        logger.error(f"Unexpected error validating command: {e}", exc_info=True)
        return False, [], f"Validation error: {e}"


def execute_command(command_list: List[str]) -> Dict:
    """
    Execute command using subprocess.run with timeout.
    
    Returns:
        Dictionary with returncode, stdout, stderr
    """
    try:
        logger.info(f"Executing command: {' '.join(command_list)}")
        
        result = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            shell=False,  # CRITICAL: Never use shell=True
        )
        
        logger.info(f"Command completed with returncode: {result.returncode}")
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {COMMAND_TIMEOUT} seconds")
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {COMMAND_TIMEOUT} seconds",
        }
    
    except Exception as e:
        logger.error(f"Error executing command: {e}", exc_info=True)
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
        }

# ============================================================================
# AUTHENTICATION
# ============================================================================

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify Bearer token from Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    if credentials.credentials != API_TOKEN:
        logger.warning(f"Invalid token attempt from client")
        raise HTTPException(status_code=403, detail="Invalid authorization token")
    
    return True

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TerminalCommandRequest(BaseModel):
    """Request model for terminal command execution."""
    command: str
    filter_contains: Optional[str] = None

class TerminalCommandResponse(BaseModel):
    """Response model for terminal command execution."""
    allowed: bool
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    timestamp: str

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Jarvas Terminal API",
        "version": "1.0.0",
        "status": "running",
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.post("/api/system/terminal/run/", response_model=TerminalCommandResponse)
async def run_terminal_command(
    request: TerminalCommandRequest,
    _: bool = Depends(verify_token),
):
    """
    Execute a whitelisted terminal command.
    
    The command is validated against a strict whitelist before execution.
    Only commands explicitly allowed in the whitelist can be executed.
    """
    command_str = request.command.strip()
    
    if not command_str:
        raise HTTPException(status_code=400, detail="Command cannot be empty")
    
    logger.info(f"Received command request: {command_str}")
    
    # Validate command
    is_allowed, parsed_command, error_message = validate_command(command_str)
    
    if not is_allowed:
        logger.warning(f"Command rejected: {command_str} - {error_message}")
        return TerminalCommandResponse(
            allowed=False,
            command=[],
            returncode=-1,
            stdout="",
            stderr="Comando não permitido pela política de segurança." if not error_message else error_message,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    # Execute command
    result = execute_command(parsed_command)
    
    # Apply optional filtering to output
    stdout = result["stdout"]
    stderr = result["stderr"]
    
    if request.filter_contains:
        substr = request.filter_contains
        logger.info(f"Filtering output for substring: '{substr}'")
        
        if stdout:
            stdout_lines = stdout.splitlines()
            stdout = "\n".join(
                line for line in stdout_lines if substr in line
            )
        
        if stderr:
            stderr_lines = stderr.splitlines()
            stderr = "\n".join(
                line for line in stderr_lines if substr in line
            )
    
    return TerminalCommandResponse(
        allowed=True,
        command=parsed_command,
        returncode=result["returncode"],
        stdout=stdout,
        stderr=stderr,
        timestamp=datetime.utcnow().isoformat(),
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Jarvas Terminal API on {HOST}:{PORT}")
    logger.info(f"Command timeout: {COMMAND_TIMEOUT}s")
    logger.info(f"Log file: {LOG_FILE}")
    
    if API_TOKEN == "CHANGE_THIS_TOKEN_IN_PRODUCTION":
        logger.warning("WARNING: Using default API token! Please change it in production!")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL.lower(),
    )

