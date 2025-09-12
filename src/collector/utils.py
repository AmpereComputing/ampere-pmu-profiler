# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import logging
import glob
import os
import subprocess
import time
import getpass
import pwd
import grp

# from pathlib import Path
from postprocessor import tda as TDA
from postprocessor import plot as PLOT
from click.testing import CliRunner

logger = logging.getLogger("app")
mux_files = glob.glob("sys/devices/*pmu*/perf_event_mux_interval_ms") + glob.glob(
    "sys/devices/arm_cmn*/perf_event_mux_interval_ms"
)


def check_root():
    if os.geteuid() != 0:
        logger.debug("lack of sudo credentials")
        raise PermissionError("Script needs sudo access")


def check_perf_availibility():
    if subprocess.call("which perf", shell=True, stdout=subprocess.DEVNULL) != 0:
        raise EnvironmentError("perf tool is not available")


def mkdir_clean(path):
    os.makedirs(path, exist_ok=True)
    for f in os.listdir(path):
        os.remove(os.path.join(path, f))


def set_perf_mux():
    for f in mux_files:
        try:
            with open(f, "r") as reader:
                current_val = int(reader.read().strip())
            if current_val == 0:
                with open(f, "w") as writer:
                    writer.write("4")
                logger.debug(f"set {f} to 4ms")
        except Exception as e:
            logger.warning(f"couldn't update {f}: {e}")


def reset_perf_mux():
    for f in mux_files:
        try:
            with open(f, "r") as reader:
                current_val = int(reader.read().strip())
            if current_val != 0:
                with open(f, "w") as writer:
                    writer.write("0")
                logger.debug(f"reset {f} to 0")
        except Exception as e:
            logger.warning(f"couldn't update {f}: {e}")


def progress_bar(seconds):
    for i in range(seconds + 1):
        print(f"[{i:04}/{seconds:04}]", end="\r")
        time.sleep(1)


def run_postprocess(
    core_count, duration, output, debug, plot, tda, event_file, persocket, src_path
):
    output = src_path.parent / output
    env = os.environ.copy()
    cmd = [
        "sudo",
        "postprocess",
        "--cpus",
        str(core_count),
        "--metric",
        str(event_file),
        "--duration",
        str(duration),
        "--output",
        str(output / "metrics.csv"),
        str(output / "core_pmu.csv"),
    ]
    if not tda:
        cmd.append(str(output / "cmn_pmu.csv"))
    if debug:
        cmd.insert(6, "--debug")
    if persocket:
        cmd.append(" --persocket")
    logger.debug(f"Running postprocess with command {cmd}")
    subprocess.run(cmd, check=True)
    env["PYTHONPATH"] = "src"
    if plot:
        runner = CliRunner()
        res = runner.invoke(PLOT.main, ["-d", str(output)])
        if res.exit_code != 0:
            raise RuntimeError(f"APP plot failed with code {res.exit_code}")
    if tda:
        runner = CliRunner()
        res = runner.invoke(TDA.main, ["-i", str(output)])
        if res.exit_code != 0:
            raise RuntimeError(f"TDA plot failed with code {res.exit_code}")


def change_ownership_recursive(path, user=None, group=None):
    # Get current user if not specified
    if user is None:
        user = os.environ.get("SUDO_USER") or getpass.getuser()
    if group is None:
        group = user

    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid

    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)

    logger.debug(f"Changed ownership of '{path}' to {user}:{group}")
