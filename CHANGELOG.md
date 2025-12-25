# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-12-25

### Added
- Created `pppoe_cred_helper` package for better maintainability.
- Implemented `RollbackPlan` for safe system recovery on exit or crash.
- Added structured logging with secret redaction.
- New CLI flags: `--dry-run`, `--json`, `--reveal-password`, `--i-am-authorized`, `--no-tty`.
- Added unit tests for extraction and rollback logic.
- Added authorization consent gate.
- Added `pyproject.toml` for standard Python packaging.

### Changed
- Refactored monolithic `pppoe.py` into modular components.
- Improved network interface detection and VLAN setup.
- Replaced brittle stdout parsing with regular expressions and structured flow.

### Fixed
- Fixed issues with stray processes by adding clean termination logic and `pkill` cleanup.
- Fixed insecure file editing by implementing atomic writes and backups.
