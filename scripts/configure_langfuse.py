"""Save canonical Langfuse settings locally without echoing API credentials."""

import getpass
from pathlib import Path
import re
from urllib.parse import urlsplit


def main():
    print('Use the API-key pair from the Langfuse Cloud project/region you will show in the demo.')
    print('These settings are separate from the ClickStack ingestion and personal API keys.')
    host = input("Langfuse host (for example https://us.cloud.langfuse.com): ").strip().rstrip("/")
    parsed = urlsplit(host)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
        or any(character.isspace() or character == "'" for character in host)
    ):
        raise SystemExit("Use the HTTPS Langfuse host without an API path.")
    public = getpass.getpass("Langfuse public key (pk-lf-..., hidden): ").strip()
    secret = getpass.getpass("Langfuse secret key (sk-lf-..., hidden): ").strip()
    if not re.fullmatch(r"pk-lf-[A-Za-z0-9_./:+=-]+", public) or not re.fullmatch(r"sk-lf-[A-Za-z0-9_./:+=-]+", secret):
        raise SystemExit("Expected a Langfuse public/secret project API-key pair.")
    updates = {
        "LANGFUSE_HOST": host,
        "LANGFUSE_PUBLIC_KEY": public,
        "LANGFUSE_SECRET_KEY": secret,
    }
    path = Path(__file__).resolve().parents[1] / ".env"
    lines = path.read_text().splitlines() if path.exists() else []
    updated = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            updated.append(f"{key}='{updates.pop(key)}'")
        else:
            updated.append(line)
    updated.extend(f"{key}='{value}'" for key, value in updates.items())
    # Protect a newly created file before any credential bytes are written.
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text("\n".join(updated) + "\n")
    print("Saved the three canonical Langfuse settings to ignored .env. Credentials were not displayed.")


if __name__ == "__main__":
    main()
