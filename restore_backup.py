"""Offline restore: stop all application windows/servers before running."""

from getpass import getpass
from pathlib import Path

from growth_planner.backup import restore_backup
from growth_planner.service import Planner


def main():
    print("Stop the browser server, API server, and desktop app before restoring.")
    print("Restore replaces the current records. A safety backup is made first.")
    planner = Planner()
    token = None
    try:
        username = input("Current faculty ID: ")
        token = planner.login(username, getpass("Current faculty password: "))
        path = Path(input("Backup file path: ").strip().strip('"'))
        if input("Type RESTORE to replace current records: ") != "RESTORE":
            print("Cancelled. Records were not restored.")
            return
        safety = restore_backup(planner, token, path)
        print("Restore complete. Sign in with the accounts/passwords from the backup.")
        print("Safety backup:", safety)
    except (ValueError, OSError) as error:
        print("Restore failed:", error)
    finally:
        if token:
            planner.logout(token)


if __name__ == "__main__":
    main()
