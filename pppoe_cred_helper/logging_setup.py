import logging
import re
from typing import Optional

class RedactingFormatter(logging.Formatter):
    """
    Formatter that removes sensitive information from logs.
    """
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, secrets: Optional[list] = None):
        super().__init__(fmt, datefmt)
        self.secrets = secrets or []

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for secret in self.secrets:
            if secret:
                msg = msg.replace(str(secret), "********")
        # Also redact patterns like Password='...' or Peer-ID='...' just in case
        msg = re.sub(r"(Password=')[^']*(')", r"\1********\2", msg)
        msg = re.sub(r"(Peer-ID=')[^']*(')", r"\1********\2", msg)
        return msg

def setup_logging(db_path: str, verbose: bool = False) -> logging.Logger:
    logger = logging.getLogger("pppoe_cred_helper")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    file_handler = logging.FileHandler(db_path, encoding="utf-8")
    file_formatter = RedactingFormatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
