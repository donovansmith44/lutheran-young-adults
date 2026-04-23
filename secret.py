#!/usr/bin/env python3
"""
secret.py — manage encrypted configs at ~/.config/event_planner/<name>.age

Commands:
  init                       Write first-time examples into the config dir
                             as encrypted .age files so you can edit them.
  edit <name>                Decrypt <name>.age, open in $EDITOR, re-encrypt
                             on save. Plaintext lives in a memfd-backed
                             tmpfile on Linux (RAM only, never on disk).
  cat  <name>                Decrypt to stdout. Use for scripts / piping.
  rekey                      Re-encrypt all .age files to the current
                             recipients.txt list. Run after adding or
                             removing a collaborator.
  list                       List encrypted files currently stored.
  pubkey                     Print this machine's public age key (paste
                             this into recipients.txt on another machine).

Names are conventional filenames that should include the extension, e.g.
  .env  |  people.yaml  |  voice.md
The ".age" suffix is added automatically on disk.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from secure_config import (  # noqa: E402
    CONFIG_DIR,
    KEY_PATH,
    RECIPIENTS_PATH,
    decrypt_bytes,
    decrypt_text,
    encrypt_bytes,
    _encrypted_path,
)

EXAMPLE_DIR = Path(__file__).resolve().parent / "examples"


def _edit_in_memory(name: str, initial: bytes) -> bytes | None:
    """Open $EDITOR on a plaintext copy. Use /dev/shm (RAM) on Linux to avoid
    touching disk. Returns edited bytes, or None if unchanged."""
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    base_tmp = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path(tempfile.gettempdir())
    suffix = "." + name.split(".")[-1] if "." in name else ""
    fd, tmp = tempfile.mkstemp(prefix="evplan-", suffix=suffix, dir=base_tmp)
    try:
        os.chmod(tmp, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(initial)
        before = Path(tmp).read_bytes()
        subprocess.run([editor, tmp], check=True)
        after = Path(tmp).read_bytes()
        return after if after != before else None
    finally:
        # overwrite before delete as a cheap wipe
        try:
            size = Path(tmp).stat().st_size
            with open(tmp, "wb") as f:
                f.write(b"\x00" * size)
        except OSError:
            pass
        Path(tmp).unlink(missing_ok=True)


def cmd_init() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.chmod(0o700)
    if not KEY_PATH.exists():
        print(f"ERROR: no private key at {KEY_PATH}. "
              "Generate one with: age-keygen -o " + str(KEY_PATH), file=sys.stderr)
        sys.exit(1)
    if not RECIPIENTS_PATH.exists():
        print(f"ERROR: no {RECIPIENTS_PATH}. "
              "Add at least your own public key to it.", file=sys.stderr)
        sys.exit(1)
    # Seed encrypted files from the repo's examples/ folder
    for example in EXAMPLE_DIR.glob("*.example"):
        name = example.name.removesuffix(".example")
        target = _encrypted_path(name)
        if target.exists():
            print(f"skip {name} (already encrypted at {target})")
            continue
        encrypt_bytes(example.read_bytes(), name)
        print(f"wrote {target}")
    print("init complete. Edit with: python3 secret.py edit <name>")


def cmd_edit(name: str) -> None:
    path = _encrypted_path(name)
    initial = decrypt_bytes(name) if path.exists() else b""
    edited = _edit_in_memory(name, initial)
    if edited is None:
        print(f"{name}: unchanged")
        return
    encrypt_bytes(edited, name)
    print(f"{name}: saved (encrypted at {path})")


def cmd_cat(name: str) -> None:
    sys.stdout.write(decrypt_text(name))


def cmd_rekey() -> None:
    """Re-encrypt every .age file in the config dir to the current recipient list."""
    n = 0
    for path in sorted(CONFIG_DIR.glob("*.age")):
        name = path.stem  # strips .age
        plaintext = decrypt_bytes(name)
        encrypt_bytes(plaintext, name)
        print(f"rekeyed {path}")
        n += 1
    print(f"done — {n} file(s)")


def cmd_list() -> None:
    for path in sorted(CONFIG_DIR.glob("*.age")):
        print(path.name.removesuffix(".age"))


def cmd_pubkey() -> None:
    pub_file = CONFIG_DIR / "key.pub"
    if pub_file.exists():
        sys.stdout.write(pub_file.read_text())
        return
    # derive from private key
    import pyrage  # type: ignore
    line = next(
        ln.strip()
        for ln in KEY_PATH.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    )
    ident = pyrage.x25519.Identity.from_str(line)
    print(ident.to_public())


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    cmd, *rest = sys.argv[1:]
    try:
        if cmd == "init":
            cmd_init()
        elif cmd == "edit":
            cmd_edit(rest[0])
        elif cmd == "cat":
            cmd_cat(rest[0])
        elif cmd == "rekey":
            cmd_rekey()
        elif cmd == "list":
            cmd_list()
        elif cmd == "pubkey":
            cmd_pubkey()
        else:
            print(__doc__)
            sys.exit(2)
    except IndexError:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
