from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class ISPConfig:
    name: str
    vlan: int

ISP_PRESETS = [
    ISPConfig("DiGi", 20),
    ISPConfig("Movistar/Tuenti/O2", 6),
    ISPConfig("Vodafone/Lowi", 100),
    ISPConfig("NEBA: Vodafone/Lowi", 24),
    ISPConfig("Jazztel", 1074),
    ISPConfig("MasMovil/PepePhone/Yoigo", 20),
    ISPConfig("Orange/Amena", 832),
    ISPConfig("Adamo", 603),
]

PPP_OPTIONS_TEMPLATE = """\
ms-dns 8.8.8.8 asyncmap 0
noauth
crtscts
lock
hide-password
modem
debug
proxyarp
lcp-echo-interval 10
lcp-echo-failure 2
noipx
plugin /etc/ppp/plugins/rp-pppoe.so
require-pap
ktune
nobsdcomp
noccp
novj
"""

DEFAULT_WORK_DIR = "/var/lib/pppoe-cred-helper"
BACKUP_DIR = f"{DEFAULT_WORK_DIR}/backups"
LOG_FILE = f"{DEFAULT_WORK_DIR}/session.log"
