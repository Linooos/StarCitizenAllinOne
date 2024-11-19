# INTRO

This script utilizes VHDX differential technology to store only a single base game data for Star Citizen, while parallelly recording the update data from different servers (such as PTU and PU). By leveraging VHDX file system differences, it efficiently manages multiple server updates with minimal storage.

# USING

1. Run command `Set-Executionpolicy Remotesigned` in `Powershell`
2. First,you should have a direct that the game data which can launch sucessfully is in. What ever PU or LIVE.
3. Free space about approximate 150GB.
4. Run exe by Addministrator.
5. Runing Script and choose `StarCitizen_Launcher.exe`.

# ATTENTION

Deploying this script requires reserving space equivalent to one base installation, approximately 150GB.

Administrator privileges are required.

The script will create some files in the RSI path; do not delete them.

The `starcitizen_backup` folder is used for script backups; if the script fails, rename it back to its original name.

Close the launcher and the file explorer for the game data directory before running the script to avoid access issues.

The script will add a scheduled task named `start_up_plan` for startup mount,do not delete it.
