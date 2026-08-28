"""One-shot Google EmbeddedSetup token exchange.

The short-lived oauth_token is read without terminal echo, exchanged in memory,
and never written to disk. Only a successful master token persists.
"""

from __future__ import annotations

import configparser
import getpass
import os
from pathlib import Path
import tempfile

from gpsoauth import exchange_token


CONFIG_PATH = Path(os.environ.get("NEST_CONFIG_PATH", "/config/nest.ini"))
ANDROID_ID = "0123456789abcdef"

DEFAULT_CONFIG = {
    "timezone": "America/Los_Angeles",
    "refresh_interval": "60",
    "fetch_range": "240",
    "cleanup_enabled": "false",
    "max_age_days": "60",
    "max_size_mb": "250000",
}


def main() -> int:
    username = input("Google account email: ").strip()
    oauth_token = getpass.getpass("EmbeddedSetup oauth_token (input hidden): ").strip()
    if not username or not oauth_token:
        print("AUTH_FAILED missing_credentials")
        return 2

    response = exchange_token(username, oauth_token, ANDROID_ID)
    oauth_token = ""
    master_token = response.get("Token")
    if not master_token:
        error = response.get("Error", "unknown_error")
        print(f"AUTH_FAILED {error}")
        return 1

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    if CONFIG_PATH.exists():
        config.read(CONFIG_PATH)
    if not config.has_section("nest"):
        config.add_section("nest")
    for key, value in DEFAULT_CONFIG.items():
        config["nest"].setdefault(key, value)
    config["nest"]["google_username"] = username
    config["nest"]["google_master_token"] = master_token

    ownership_source = CONFIG_PATH if CONFIG_PATH.exists() else CONFIG_PATH.parent
    ownership = ownership_source.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="nest.ini.", dir=CONFIG_PATH.parent, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        try:
            os.fchown(descriptor, ownership.st_uid, ownership.st_gid)
        except PermissionError:
            # Some Docker Desktop bind mounts do not permit changing ownership.
            pass
        with os.fdopen(descriptor, "w", encoding="utf-8") as config_file:
            config.write(config_file)
            config_file.flush()
            os.fsync(config_file.fileno())
        temporary_path.replace(CONFIG_PATH)
        CONFIG_PATH.chmod(0o600)
    finally:
        temporary_path.unlink(missing_ok=True)

    print("AUTH_OK master_token_saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
