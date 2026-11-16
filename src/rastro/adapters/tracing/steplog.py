import json
import logging
import sys

_log = logging.getLogger("rastro.steps")
if not _log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(message)s"))
    _log.addHandler(_h)
    _log.setLevel(logging.INFO)
    _log.propagate = False


def log_step(thread_id: str, kind: str, payload: dict) -> None:
    _log.info(
        json.dumps({"thread": thread_id, "step": kind, **payload}, ensure_ascii=False, default=str)
    )
