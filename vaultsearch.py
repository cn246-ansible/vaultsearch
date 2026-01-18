#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#     "ansible",
# ]
# ///
# ruff: noqa: T201
"""Quickly "grep" ansible vault files.

Recursively search current working directory:
  vaultgrep "searchterm"

Use regex for the search query:
  vaultgrep "searchterm|anotherterm" /group_vars/all

Recursively search specific directory:
  vaultgrep "searchterm" host_vars/myhost
"""
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from ansible import constants as c
from ansible.cli import CLI
from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib

# Color codes
BGRN = "\033[01;92m"
BRED = "\033[01;31m"
BYEL = "\033[01;33m"
ENDC = "\033[0m"


def parse_arguments() -> tuple[re.Pattern[str], Path]:
    """Parse and validate command line arguments.

    Returns:
        tuple: Compiled regex pattern and search start path

    Raises:
        SystemExit: If arguments are invalid
    """
    if len(sys.argv) < 2:
        print(f"{BRED}Error: Search term required!{ENDC}", file=sys.stderr)
        print()
        print(__doc__)
        sys.exit(1)

    searchterm: str = sys.argv[1]
    try:
        rxsearch: re.Pattern[str] = re.compile(searchterm)
    except re.error as e:
        print(f"{BRED}Error: Invalid regex pattern: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

    minarg: int = 2
    search_start_path: Path = Path(sys.argv[2]) if len(sys.argv) > minarg else Path.cwd()

    if not search_start_path.exists():
        print(f"{BRED}Error: Path does not exist: {search_start_path}{ENDC}", file=sys.stderr)
        sys.exit(1)

    return rxsearch, search_start_path


def is_vault_file(file_path: str) -> bool:
    """Check first line of file for the string '$ANSIBLE_VAULT'.

    Args:
        file_path: File path to search

    Returns:
        True if vault file, False otherwise
    """
    try:
        with Path(file_path).open("rb") as f:
            first_line = f.readline()
            return b"$ANSIBLE_VAULT" in first_line
    except (OSError, PermissionError) as e:
        print(f"{BYEL}Warning: Cannot read {file_path}: {e}{ENDC}", file=sys.stderr)
        return False


def find_vault_files(search_path: Path) -> Iterator[str]:
    """Recursively search for Ansible vault files in the provided path.

    Args:
        search_path: Where to start searching for vault files

    Yields:
        Path of all vault files in search_path
    """
    try:
        for p in os.scandir(search_path):
            try:
                if p.is_file(follow_symlinks=False) and p.stat().st_size > 0:
                    if is_vault_file(p.path):
                        yield p.path
                elif p.is_dir(follow_symlinks=False) and p.name != ".git":
                    yield from find_vault_files(Path(p.path))
            except (OSError, PermissionError) as e:
                print(f"{BYEL}Warning: Cannot access {p.path}: {e}{ENDC}", file=sys.stderr)
                continue
    except (OSError, PermissionError) as e:
        print(f"{BYEL}Warning: Cannot scan directory {search_path}: {e}{ENDC}", file=sys.stderr)


def decrypt_vault_file(file_path: str, vault: VaultLib) -> str | None:
    """Decrypt vault encrypted files.

    Args:
        file_path: Path of file to decrypt
        vault: VaultLib instance for decryption

    Returns:
        Decrypted data as string, or None if decryption fails
    """
    try:
        with Path(file_path).open("r", encoding="utf-8") as f:
            decrypted = vault.decrypt(f.read())
            return decrypted.decode("utf-8", errors="ignore")
    except AnsibleError as e:
        print(f"{BYEL}Warning: Cannot decrypt {file_path}: {e}{ENDC}", file=sys.stderr)
        return None
    except (OSError, PermissionError) as e:
        print(f"{BYEL}Warning: Cannot read {file_path}: {e}{ENDC}", file=sys.stderr)
        return None


def highlight_matches(line: str, pattern: re.Pattern[str]) -> str:
    """Highlight all regex matches in a line with color.

    Args:
        line: Line to search and highlight
        pattern: Compiled regex pattern

    Returns:
        Line with matches highlighted in red
    """
    return pattern.sub(lambda m: f"{BRED}{m[0]}{ENDC}", line).lstrip()


def main() -> None:
    """Search vault files for pattern and display results.

    Recursively loops over files in the given directory looking for files where
    the first line contains the string: $ANSIBLE_VAULT.
    Decrypts the vault file and searches for the term against the bulk data.
    If it finds the term, split lines and return the file name and the line(s)
    with the search term highlighted.
    """
    rxsearch, search_start_path = parse_arguments()

    # Initialize Ansible vault
    loader = DataLoader()
    id_list = c.DEFAULT_VAULT_IDENTITY_LIST
    try:
        vault_secret = CLI.setup_vault_secrets(loader=loader, vault_ids=id_list)
    except AnsibleError as e:
        print(f"{BRED}Error: Failed to setup vault secrets: {e}{ENDC}", file=sys.stderr)
        sys.exit(1)

    vault = VaultLib(vault_secret)

    found_any = False

    for file in find_vault_files(search_start_path):
        decrypted_data = decrypt_vault_file(file, vault)
        if decrypted_data is None:
            continue

        if rxsearch.search(decrypted_data):
            found_any = True
            print(f"{BGRN}{file}{ENDC}")

            matching_lines = {line for line in decrypted_data.splitlines() if rxsearch.search(line)}

            for line in matching_lines:
                highlighted = highlight_matches(line, rxsearch)
                print(f"  {highlighted}")
            print()

    if not found_any:
        print(f"No matches found for pattern: {rxsearch.pattern}")


if __name__ == "__main__":
    main()

# vim: ft=python ts=4 sts=4 sw=4 sr et
