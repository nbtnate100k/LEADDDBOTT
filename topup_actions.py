"""Approve / reject manual top-ups (shared by Telegram bot and pay portal)."""

from __future__ import annotations

from pending_topups import get_pending, set_status
from users_persist import load_users as _load_users, save_users as _save_users

_USER_DEFAULTS: dict = {
    "balance": 0.0,
    "cart": [],
    "vip": False,
    "total_deposits": 0.0,
    "total_spent": 0.0,
    "status": "active",
}


def try_accept_topup(pid: str) -> tuple[bool, str, dict | None]:
    rec = get_pending(pid)
    if not rec or rec.get("status") != "pending":
        return False, "Already handled or invalid.", None
    uid = int(rec["user_id"])
    amt = float(rec["amount_usd"])
    users = _load_users()
    uid_s = str(uid)
    if uid_s not in users:
        users[uid_s] = {**_USER_DEFAULTS}
    entry = {**_USER_DEFAULTS, **users.get(uid_s, {})}
    new_bal = round(float(entry.get("balance", 0.0)) + amt, 2)
    entry["balance"] = new_bal
    users[uid_s] = {**users.get(uid_s, {}), **entry}
    _save_users(users)
    set_status(pid, "accepted")
    return True, "", {"rec": rec, "user_id": uid, "new_balance": new_bal, "amount_usd": amt}


def try_reject_topup(pid: str) -> tuple[bool, str, dict | None]:
    rec = get_pending(pid)
    if not rec or rec.get("status") != "pending":
        return False, "Already handled or invalid.", None
    uid = int(rec["user_id"])
    set_status(pid, "rejected")
    return True, "", {"rec": rec, "user_id": uid, "amount_usd": float(rec["amount_usd"])}
