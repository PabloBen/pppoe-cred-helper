import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pppoe_cred_helper.system.files")

def backup_file(path: Path, backup_dir: Path) -> Optional[Path]:
    """
    Create a timestamped backup of a file.
    """
    if not path.exists():
        return None
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{path.name}.{timestamp}.bak"
    
    try:
        shutil.copy2(path, backup_path)
        logger.info("Backup created: %s", backup_path)
        return backup_path
    except Exception as e:
        logger.error("Failed to create backup for %s: %s", path, e)
        return None

def atomic_write(path: Path, content: str, dry_run: bool = False):
    """
    Write content to a file atomically via a temporary file.
    """
    if dry_run:
        logger.info("[DRY-RUN] Atomic write to %s", path)
        return

    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(path)
        logger.debug("Successfully updated %s", path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

def restore_file(original_path: Path, backup_path: Path, dry_run: bool = False):
    """
    Restore a file from its backup.
    """
    if dry_run:
        logger.info("[DRY-RUN] Restore %s from %s", original_path, backup_path)
        return

    try:
        shutil.copy2(backup_path, original_path)
        logger.info("Restored %s from backup", original_path)
    except Exception as e:
        logger.error("Failed to restore %s: %s", original_path, e)
