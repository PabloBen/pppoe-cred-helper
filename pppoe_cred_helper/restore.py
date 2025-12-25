import logging
import traceback
from typing import Callable, List

logger = logging.getLogger("pppoe_cred_helper.restore")

class RollbackPlan:
    """
    A stack of undo actions to be executed in LIFO order.
    """
    def __init__(self):
        self._actions: List[Tuple[str, Callable]] = []

    def push(self, description: str, func: Callable, *args, **kwargs):
        """
        Add a rollback action.
        """
        self._actions.append((description, lambda: func(*args, **kwargs)))
        logger.debug("Pushed rollback action: %s", description)

    def execute(self):
        """
        Execute all rollback actions in reverse order.
        """
        logger.info("Executing rollback plan (%d actions)...", len(self._actions))
        while self._actions:
            description, func = self._actions.pop()
            try:
                logger.info("Undoing: %s", description)
                func()
            except Exception as e:
                logger.error("Failed to undo '%s': %s", description, e)
                logger.debug(traceback.format_exc())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.warning("Rollback triggered by exception: %s", exc_val)
        self.execute()
