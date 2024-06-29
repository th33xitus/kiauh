# ======================================================================= #
#  Copyright (C) 2020 - 2024 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

import os
import re
import select
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, Popen, run
from typing import List, Literal

from utils.constants import SYSTEMD
from utils.fs_utils import check_file_exist
from utils.input_utils import get_confirm
from utils.logger import Logger

SysCtlServiceAction = Literal[
    "start",
    "stop",
    "restart",
    "reload",
    "enable",
    "disable",
    "mask",
    "unmask",
]
SysCtlManageAction = Literal["daemon-reload", "reset-failed"]


def kill(opt_err_msg: str = "") -> None:
    """
    Kills the application |
    :param opt_err_msg: an optional, additional error message
    :return: None
    """

    if opt_err_msg:
        Logger.print_error(opt_err_msg)
    Logger.print_error("A critical error has occured. KIAUH was terminated.")
    sys.exit(1)


def check_python_version(major: int, minor: int) -> bool:
    """
    Checks the python version and returns True if it's at least the given version
    :param major: the major version to check
    :param minor: the minor version to check
    :return: bool
    """
    if not (sys.version_info.major >= major and sys.version_info.minor >= minor):
        Logger.print_error("Versioncheck failed!")
        Logger.print_error(f"Python {major}.{minor} or newer required.")
        return False
    return True


def parse_packages_from_file(source_file: Path) -> List[str]:
    """
    Read the package names from bash scripts, when defined like:
    PKGLIST="package1 package2 package3" |
    :param source_file: path of the sourcefile to read from
    :return: A list of package names
    """

    packages = []
    with open(source_file, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("PKGLIST="):
                line = line.replace('"', "")
                line = line.replace("PKGLIST=", "")
                line = line.replace("${PKGLIST}", "")
                packages.extend(line.split())

    return packages


def create_python_venv(target: Path) -> None:
    """
    Create a python 3 virtualenv at the provided target destination |
    :param target: Path where to create the virtualenv at
    :return: None
    """
    Logger.print_status("Set up Python virtual environment ...")
    if not target.exists():
        try:
            venv.create(target, with_pip=True)
            Logger.print_ok("Setup of virtualenv successful!")
        except OSError as e:
            Logger.print_error(f"Error setting up virtualenv:\n{e}")
            raise
        except CalledProcessError as e:
            Logger.print_error(f"Error setting up virtualenv:\n{e.output.decode()}")
            raise
    else:
        if get_confirm("Virtualenv already exists. Re-create?", default_choice=False):
            try:
                shutil.rmtree(target)
                create_python_venv(target)
            except OSError as e:
                log = f"Error removing existing virtualenv: {e.strerror}"
                Logger.print_error(log, False)
                raise
        else:
            Logger.print_info("Skipping re-creation of virtualenv ...")


def update_python_pip(target: Path) -> None:
    """
    Updates pip in the provided target destination |
    :param target: Path of the virtualenv
    :return: None
    """
    Logger.print_status("Updating pip ...")
    try:
        pip_location = target.joinpath("bin/pip")
        pip_exists = check_file_exist(pip_location)
        if not pip_exists:
            raise FileNotFoundError("Error updating pip! Not found.")

        command = [pip_location, "install", "-U", "pip"]
        result = run(command, stderr=PIPE, text=True)
        if result.returncode != 0 or result.stderr:
            Logger.print_error(f"{result.stderr}", False)
            Logger.print_error("Updating pip failed!")
            return

        Logger.print_ok("Updating pip successful!")
    except FileNotFoundError as e:
        Logger.print_error(e)
        raise
    except CalledProcessError as e:
        Logger.print_error(f"Error updating pip:\n{e.output.decode()}")
        raise


def install_python_requirements(target: Path, requirements: Path) -> None:
    """
    Installs the python packages based on a provided requirements.txt |
    :param target: Path of the virtualenv
    :param requirements: Path to the requirements.txt file
    :return: None
    """
    try:
        # always update pip before installing requirements
        update_python_pip(target)

        Logger.print_status("Installing Python requirements ...")
        command = [
            target.joinpath("bin/pip"),
            "install",
            "-r",
            f"{requirements}",
        ]
        result = run(command, stderr=PIPE, text=True)

        if result.returncode != 0 or result.stderr:
            Logger.print_error(f"{result.stderr}", False)
            Logger.print_error("Installing Python requirements failed!")
            return

        Logger.print_ok("Installing Python requirements successful!")
    except CalledProcessError as e:
        log = f"Error installing Python requirements:\n{e.output.decode()}"
        Logger.print_error(log)
        raise


def update_system_package_lists(silent: bool, rls_info_change=False) -> None:
    """
    Updates the systems package list |
    :param silent: Log info to the console or not
    :param rls_info_change: Flag for "--allow-releaseinfo-change"
    :return: None
    """
    cache_mtime = 0
    cache_files = [
        Path("/var/lib/apt/periodic/update-success-stamp"),
        Path("/var/lib/apt/lists"),
    ]
    for cache_file in cache_files:
        if cache_file.exists():
            cache_mtime = max(cache_mtime, os.path.getmtime(cache_file))

    update_age = int(time.time() - cache_mtime)
    update_interval = 6 * 3600  # 48hrs

    if update_age <= update_interval:
        return

    if not silent:
        Logger.print_status("Updating package list...")

    try:
        command = ["sudo", "apt-get", "update"]
        if rls_info_change:
            command.append("--allow-releaseinfo-change")

        result = run(command, stderr=PIPE, text=True)
        if result.returncode != 0 or result.stderr:
            Logger.print_error(f"{result.stderr}", False)
            Logger.print_error("Updating system package list failed!")
            return

        Logger.print_ok("System package list update successful!")
    except CalledProcessError as e:
        Logger.print_error(f"Error updating system package list:\n{e.stderr.decode()}")
        raise


def check_package_install(packages: List[str]) -> List[str]:
    """
    Checks the system for installed packages |
    :param packages: List of strings of package names
    :return: A list containing the names of packages that are not installed
    """
    not_installed = []
    for package in packages:
        command = ["dpkg-query", "-f'${Status}'", "--show", package]
        result = run(
            command,
            stdout=PIPE,
            stderr=DEVNULL,
            text=True,
        )
        if "installed" not in result.stdout.strip("'").split():
            not_installed.append(package)

    return not_installed


def install_system_packages(packages: List[str]) -> None:
    """
    Installs a list of system packages |
    :param packages: List of system package names
    :return: None
    """
    try:
        command = ["sudo", "apt-get", "install", "-y"]
        for pkg in packages:
            command.append(pkg)
        run(command, stderr=PIPE, check=True)

        Logger.print_ok("Packages installed successfully.")
    except CalledProcessError as e:
        Logger.print_error(f"Error installing packages:\n{e.stderr.decode()}")
        raise


# this feels hacky and not quite right, but for now it works
# see: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
def get_ipv4_addr() -> str:
    """
    Helper function that returns the IPv4 of the current machine
    by opening a socket and sending a package to an arbitrary IP. |
    :return: Local IPv4 of the current machine
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(("192.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def download_file(url: str, target: Path, show_progress=True) -> None:
    """
    Helper method for downloading files from a provided URL |
    :param url: the url to the file
    :param target: the target path incl filename
    :param show_progress: show download progress or not
    :return: None
    """
    try:
        if show_progress:
            urllib.request.urlretrieve(url, target, download_progress)
            sys.stdout.write("\n")
        else:
            urllib.request.urlretrieve(url, target)
    except urllib.error.HTTPError as e:
        Logger.print_error(f"Download failed! HTTP error occured: {e}")
        raise
    except urllib.error.URLError as e:
        Logger.print_error(f"Download failed! URL error occured: {e}")
        raise
    except Exception as e:
        Logger.print_error(f"Download failed! An error occured: {e}")
        raise


def download_progress(block_num, block_size, total_size) -> None:
    """
    Reporthook method for urllib.request.urlretrieve() method call in download_file() |
    :param block_num:
    :param block_size:
    :param total_size: total filesize in bytes
    :return: None
    """
    downloaded = block_num * block_size
    percent = 100 if downloaded >= total_size else downloaded / total_size * 100
    mb = 1024 * 1024
    progress = int(percent / 5)
    remaining = "-" * (20 - progress)
    dl = f"\rDownloading: [{'#' * progress}{remaining}]{percent:.2f}% ({downloaded / mb:.2f}/{total_size / mb:.2f}MB)"
    sys.stdout.write(dl)
    sys.stdout.flush()


def set_nginx_permissions() -> None:
    """
    Check if permissions of the users home directory
    grant execution rights to group and other and set them if not set.
    Required permissions for NGINX to be able to serve Mainsail/Fluidd.
    This seems to have become necessary with Ubuntu 21+. |
    :return: None
    """
    cmd = f"ls -ld {Path.home()} | cut -d' ' -f1"
    homedir_perm = run(cmd, shell=True, stdout=PIPE, text=True)
    homedir_perm = homedir_perm.stdout

    if homedir_perm.count("x") < 3:
        Logger.print_status("Granting NGINX the required permissions ...")
        run(["chmod", "og+x", Path.home()])
        Logger.print_ok("Permissions granted.")


def cmd_sysctl_service(name: str, action: SysCtlServiceAction) -> None:
    """
    Helper method to execute several actions for a specific systemd service. |
    :param name: the service name
    :param action: Either "start", "stop", "restart" or "disable"
    :return: None
    """
    try:
        Logger.print_status(f"{action.capitalize()} {name} ...")
        run(["sudo", "systemctl", action, name], stderr=PIPE, check=True)
        Logger.print_ok("OK!")
    except CalledProcessError as e:
        log = f"Failed to {action} {name}: {e.stderr.decode()}"
        Logger.print_error(log)
        raise


def cmd_sysctl_manage(action: SysCtlManageAction) -> None:
    try:
        run(["sudo", "systemctl", action], stderr=PIPE, check=True)
    except CalledProcessError as e:
        log = f"Failed to run {action}: {e.stderr.decode()}"
        Logger.print_error(log)
        raise


def service_instance_exists(name: str, exclude: List[str] = None) -> bool:
    """
    Checks if a systemd service instance exists.
    :param name: the service name
    :param exclude: List of strings of service names to exclude
    :return: True if the service exists, False otherwise
    """
    exclude = exclude or []
    pattern = re.compile(f"^{name}(-[0-9a-zA-Z]+)?.service$")
    service_list = [
        Path(SYSTEMD, service)
        for service in SYSTEMD.iterdir()
        if pattern.search(service.name) and not any(s in service.name for s in exclude)
    ]
    return any(service_list)


def log_process(process: Popen) -> None:
    """
    Helper method to print stdout of a process in near realtime to the console.
    :param process: Process to log the output from
    :return: None
    """
    while True:
        reads = [process.stdout.fileno()]
        ret = select.select(reads, [], [])
        for fd in ret[0]:
            if fd == process.stdout.fileno():
                line = process.stdout.readline()
                if line:
                    print(line.strip(), flush=True)
                else:
                    break

        if process.poll() is not None:
            break