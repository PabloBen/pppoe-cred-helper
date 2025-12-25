import re
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class Credentials:
    username: str
    password: str

# Example TShark output line:
#   1 0.000000000       10.0.0.1 → 10.0.0.2         PAP 60 Authenticate-Request (Peer-ID='user@isp', Password='password123')

USER_RE = re.compile(r"Peer-ID='([^']*)'")
PASS_RE = re.compile(r"Password='([^']*)'")

def parse_pap_line(line: str) -> Optional[Credentials]:
    """
    Parse a single line of tshark output for PAP credentials.
    Returns a Credentials object if found, else None.
    """
    if "Authenticate-Request" not in line:
        return None

    user_match = USER_RE.search(line)
    pass_match = PASS_RE.search(line)

    if user_match and pass_match:
        return Credentials(
            username=user_match.group(1),
            password=pass_match.group(1)
        )
    
    return None

def mask_password(password: str) -> str:
    """Mask a password for safe display."""
    if len(password) <= 2:
        return "*" * len(password)
    return password[0] + "*" * (len(password) - 2) + password[-1]
