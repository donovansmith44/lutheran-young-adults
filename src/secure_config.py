"""
Read/write encrypted config files at ~/.config/event_planner/<name>.age.

Uses age (via pyrage) with an x25519 keypair generated once at setup time.
The private key lives at ~/.config/event_planner/key.txt (chmod 600).
Everything here decrypts in memory — plaintext never touches disk.
"""
from __future__ import annotations

import os
from pathlib import Path

import pyrage
import yaml

CONFIG_DIR = Path.home() / ".config" / "event_planner"
KEY_PATH = CONFIG_DIR / "key.txt"
REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPIENTS_PATH = REPO_ROOT / "recipients.txt"


def _private_identity() -> pyrage.x25519.Identity:
    """The local machine's own private key (never shared)."""
    line = next(
        ln.strip()
        for ln in KEY_PATH.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    )
    return pyrage.x25519.Identity.from_str(line)


def _public_recipients() -> list[pyrage.x25519.Recipient]:
    """All public keys that should be able to decrypt — read from the
    repo-tracked recipients.txt. Each collaborator has their own entry.
    Comments and blank lines ignored."""
    if not RECIPIENTS_PATH.exists():
        raise RuntimeError(
            f"no recipients file at {RECIPIENTS_PATH}. "
            "Add at least one age public key (age1...) to it."
        )
    keys = [
        ln.strip()
        for ln in RECIPIENTS_PATH.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if not keys:
        raise RuntimeError(f"recipients file {RECIPIENTS_PATH} is empty")
    return [pyrage.x25519.Recipient.from_str(k) for k in keys]


def _encrypted_path(name: str) -> Path:
    return CONFIG_DIR / f"{name}.age"


def decrypt_bytes(name: str) -> bytes:
    return pyrage.decrypt(_encrypted_path(name).read_bytes(), [_private_identity()])


def decrypt_text(name: str) -> str:
    return decrypt_bytes(name).decode("utf-8")


def decrypt_yaml(name: str) -> dict | list:
    return yaml.safe_load(decrypt_text(name))


def encrypt_bytes(content: bytes, name: str) -> Path:
    """Encrypt to ALL public keys in recipients.txt — any one of their
    corresponding private keys can decrypt."""
    ciphertext = pyrage.encrypt(content, _public_recipients())
    path = _encrypted_path(name)
    path.write_bytes(ciphertext)
    path.chmod(0o600)
    return path


def load_env() -> dict[str, str]:
    """Parse a dotenv-style encrypted file (.env.age) into a dict.

    Lines of the form KEY=VALUE. Comments and blanks ignored. Values may be
    quoted; surrounding quotes are stripped. Also injects into os.environ for
    libraries that read from there directly.
    """
    env: dict[str, str] = {}
    for line in decrypt_text(".env").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v
        os.environ.setdefault(k.strip(), v)
    return env


def has(name: str) -> bool:
    return _encrypted_path(name).exists()
