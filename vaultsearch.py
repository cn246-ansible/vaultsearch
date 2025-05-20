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
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultLib

# Vars for decrypting vault files using Ansible modules
loader = DataLoader()
id_list = c.DEFAULT_VAULT_IDENTITY_LIST
vault_secret = CLI.setup_vault_secrets(loader=loader, vault_ids=id_list)
vault = VaultLib(vault_secret)

# Color codes
BGRN = "\033[01;92m"
BRED = "\033[01;31m"
ENDC = "\033[0m"

# First argument is search term
searchterm: str = sys.argv[1]
rxsearch: re.Pattern[str] = re.compile(searchterm)

# Second (optional) argument is path to search
minarg: int = 2
search_start_path: Path = Path(sys.argv[2]) if len(sys.argv) > minarg else Path.cwd()


def is_vault_file(file_path: str) -> bool:
    """Check first line of file for the string '$ANSIBLE_VAULT'.

    Parameters:
        file_path: File path to search

    Returns:
        bool: True if vault file
    """
    with Path(file_path).open("r", encoding="utf-8", errors="ignore") as f:
        return "$ANSIBLE_VAULT" in f.readline()


def find_vault_files(search_path: Path) -> Iterator:
    """Recursively search for Ansible vault files in the provided path.

    Parameters:
        search_path (str): where to start searching for vault files

    Yields:
        p.path (str): path of all files in search_path
    """
    for p in os.scandir(search_path):
        if (p.is_file() and p.stat().st_size > 0) and is_vault_file(p.path):
            yield p.path
        elif p.is_dir() and p.name != ".git":
            yield from find_vault_files(p.path)


def decrypt_vault_file(file_path: str) -> str:
    """Decrypts vault encrypted files.

    Parameters:
        file_path (str) - Path of file to decrypt

    Returns:
        decrypted (str) - Bulk decrypted data
    """
    with Path(file_path).open("r", encoding="utf-8") as f:
        decrypted = vault.decrypt(f.read())
        return decrypted.decode("utf-8", errors="ignore")


def search_line(contents: str) -> str | None:
    """Search contents for search term and return the result.

    Parameters:
        contents (str): Content to search

    Returns:
        Matching result with search term colored red
    """
    match: re.Match[str] | None = rxsearch.search(contents)
    if match:
        return rxsearch.sub(f"{BRED}{match[0]}{ENDC}", contents).lstrip()
    return None


def main() -> str | None:
    """Combine the functions.

    Recursively loops over files in the given directory looking for files where
    the first line contains the string: $ANSIBLE_VAULT.
    Decrypts the vault file and searches for the term against the bulk data.
    If it finds the term, split lines and return the file name and the line(s)
    with the search term highlighted

    Prints:
        Formatted lines matching search term
    """
    for file in find_vault_files(search_start_path):
        decrypted_data: str = decrypt_vault_file(file)
        if rxsearch.search(decrypted_data):
            print(f"{BGRN}{file}{ENDC}")
            line_match: set = {
                x for x in decrypted_data.splitlines() if rxsearch.search(x)
            }
            for line in line_match:
                output = search_line(line)
                print(f"  {output}")
            print()


if __name__ == "__main__":
    main()

# vim: ft=python ts=4 sts=4 sw=4 sr et
