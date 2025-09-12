# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import subprocess
import logging

logger = logging.getLogger("app")


class CPUDetector:
    @staticmethod
    def detect(event_file, tda):
        impl = subprocess.getoutput(
            "grep implementer /proc/cpuinfo | head -1 | awk '{print $4}'"
        )
        part = subprocess.getoutput(
            "grep part /proc/cpuinfo | head -1 | awk '{print $4}'"
        )
        dmipart = subprocess.getoutput(
            "dmidecode -t processor | grep -m 1 'Part Number' | awk '{print $3}'"
        )

        cpu = "unknown"
        if impl == "0x41" and part == "0xd0c":
            cpu = "Altra Family"
            event_file = "events_altra.txt"
            if tda:
                logger.warning("Currently Altra Family don't support TDA")
        elif impl == "0xc0" and part == "0xac3":
            cpu = "AmpereOne AC03"
            event_file = "events_ampereone_ac03.txt"
            if tda:
                event_file = "events_tda_ac03.txt"
        elif impl == "0xc0" and part == "0xac4":
            if dmipart.endswith("X"):
                cpu = "AmpereOne AC04"
                event_file = "events_ampereone_ac04.txt"
                if tda:
                    event_file = "events_tda_ac04.txt"
            elif dmipart.endswith("M"):
                cpu = "AmpereOne AC04_1"
                event_file = "events_ampereone_ac04_1.txt"
                if tda:
                    event_file = "events_tda_ac04.txt"
        logger.info(f"CPU detected: {cpu}, eventfile: {event_file}")
        return {"arch": cpu, "event_file": event_file}
