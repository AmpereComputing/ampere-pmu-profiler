# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import logging
from pathlib import Path
import subprocess
import re
import sys

logger = logging.getLogger("app")
src_path = Path(__file__).resolve().parents[1]


class EventParser:
    @staticmethod
    def get_events(event_file, cpu_info):
        try:
            perf_list = subprocess.check_output(["perf", "list"], text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to execute perf list: {e}")
        arm_cmn_0, arm_cmn_1 = EventParser.__get_arm_cmn_names(perf_list)
        support_cmn = 1 if "arm_cmn" in perf_list else 0
        events_core = ""
        events_cmn = ""
        events_type = 99
        group_s = 0

        with open(event_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line == "events_core":
                    events_type = 0
                    continue
                if line == "events_cmn":
                    events_type = 1
                    continue
                if line == ";":
                    break

                if line == "{":
                    group_s = 1
                    continue
                if line == "}":
                    if events_type == 0:
                        events_core = events_core.rstrip(",") + "}',"
                    elif events_type == 1:
                        events_cmn = events_cmn.rstrip(",") + "}',"
                    continue
                if line.startswith("ARM_CMN"):
                    if not support_cmn:
                        raise RuntimeError(
                            f"Error: arm_cmn PMU driver isn't available. {event_file} contains CMN events. Please Update the kernel or use events.txt instead"
                        )
                    if group_s:
                        line = "'{" + line
                        group_s = 0
                    events_cmn += line + ","
                else:
                    event = line.split("|")
                    pname = event[0].strip()
                    hex_val = event[1].strip() if len(event) > 1 else ""
                    name = pname.split(":")[0]
                    support_core = 1 if re.search(rf"\b{name}\b", perf_list) else 0
                    if support_core == 0 and hex_val:
                        pname = hex_val
                    if group_s:
                        pname = "'{" + pname
                        group_s = 0
                    events_core += pname + ","

        if events_core:
            events_core = events_core.rstrip(",")
            logger.debug(f"core events from eventlist: {events_core}")

        if events_cmn:
            events_cmn = (
                events_cmn.rstrip(",")
                .replace("ARM_CMN_0", arm_cmn_0)
                .replace("ARM_CMN_1", arm_cmn_1)
            )
            logger.debug(f"cmn events from eventlist: {events_cmn}")

        return {"core": events_core, "cmn": events_cmn}

    @staticmethod
    def __get_arm_cmn_names(perf_list):
        try:
            lscpu = subprocess.run(["lscpu"], stdout=subprocess.PIPE, text=True)
            for line in lscpu.stdout.splitlines():
                if "Socket(s):" in line:
                    num_sockets = int(line.split(":")[1].rstrip())
            logger.info(f"Number of sockets: {num_sockets}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Unable to get number of sockets: {e}")

        wp_lines = [line for line in perf_list.splitlines() if "watchpoint_up" in line]

        if num_sockets == 1:
            if len(wp_lines) < 1:
                logger.warning("watchpoint_up not found for socket 0")
                sys.exit(1)
            arm_cmn_0 = wp_lines[0].split("/")[0].strip()
            return arm_cmn_0, ""

        elif num_sockets == 2:
            if len(wp_lines) < 2:
                logger.warning("watchpoint_up not found for socket 0 or socket 1")
                sys.exit(1)
            arm_cmn_0 = wp_lines[0].split("/")[0].strip()
            arm_cmn_1 = wp_lines[1].split("/")[0].strip()
            return arm_cmn_0, arm_cmn_1
        else:
            logger.warning(f"Unexpected socket number: {num_sockets}!!")
            sys.exit(1)
