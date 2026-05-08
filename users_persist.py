"""Atomic persistence for users.json (balances, carts, etc.).

Corrupt or half-written JSON + a single save used to be able to wipe the file
and show everyone $0. We use temp-then-rename writes and users.json.bak recovery.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

from data_paths import data_dir

logger = logging.getLogger(__name__)

USERS_PATH = data_dir() / "users.json"
USERS_BAK_PATH = data_dir() / "users.json.bak"


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.error("%s: expected a JSON object", path)
            return None
        return data
    except (json.JSONDecodeError, OSError, TypeError) as e:
        logger.warning("Cannot read %s: %s", path, e)
        return None


def _atomic_write_dict(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix="users_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_users() -> dict:
    data = _read_json(USERS_PATH)
    if data is not None:
        return data

    logger.error(
        "users.json is missing or invalid (crash mid-write, wrong LEADBOT_DATA_DIR, "
        "disk full, or manual edit). Trying users.json.bak."
    )
    bak = _read_json(USERS_BAK_PATH)
    if bak is not None:
        logger.warning("Restoring users.json from users.json.bak.")
        try:
            _atomic_write_dict(USERS_PATH, bak)
        except OSError as e:
            logger.error("Could not write restored users.json: %s", e)
        return bak

    logger.error(
        "No valid users.json or users.json.bak — balances will look empty until you restore data."
    )
    return {}


def save_users(users: dict) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USERS_PATH.is_file():
        prev = _read_json(USERS_PATH)
        if prev is not None:
            try:
                shutil.copyfile(USERS_PATH, USERS_BAK_PATH)
            except OSError as e:
                logger.warning("Could not copy users.json to users.json.bak: %s", e)
        else:
            logger.warning(
                "users.json exists but is not valid JSON; not overwriting users.json.bak "
                "(fix users.json manually or copy users.json.bak over users.json)."
            )

    _atomic_write_dict(USERS_PATH, users)
