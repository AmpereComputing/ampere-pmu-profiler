# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import subprocess
import time
import signal
from collector.cpu import CPUDetector
from collector.events import EventParser
from collector.utils import (
    check_root,
    check_perf_availibility,
    mkdir_clean,
    set_perf_mux,
    reset_perf_mux,
    progress_bar,
    run_postprocess,
    change_ownership_recursive,
)
import logging
from pathlib import Path
import click

logger = logging.getLogger("app")
src_path = Path(__file__).resolve().parents[1]
events_path = src_path / "events"


class Profiler:
    def __init__(
        self,
        duration,
        interval,
        job,
        cores,
        persocket,
        plot,
        output,
        event_file,
        tda,
        debug,
        delay,
    ):
        self.duration = duration
        self.interval_ms = interval * 1000
        self.workload = job
        self.cores = cores
        self.persocket = persocket
        self.plot = plot
        self.output = output
        self.event_file = event_file
        self.tda = tda
        self.debug = debug
        self.process_queue = []
        self.core_count = 0
        self.delay = delay
        self.cpu_info = None

    def run(self):
        check_root()
        check_perf_availibility()
        mkdir_clean(self.output)

        if self.duration < 10:
            raise ValueError("Sample duration must be >= 10 seconds")

        if not self.event_file:
            logger.debug("no event file provided")
            logger.info("Detecting CPU")
            cpu_info = CPUDetector.detect(self.event_file, self.tda)
            self.event_file = events_path / cpu_info["event_file"]
            self.cpu_info = cpu_info["arch"]
        else:
            logger.info(f"Using eventlist: {self.event_file}")
            if not os.path.exists(self.event_file):
                raise FileNotFoundError(f"Event file '{self.event_file}' not found")
        if self.tda:
            if self.cpu_info == "Altra Family" or self.event_file == "events_altra.txt":
                raise click.UsageError("TDA isn't supported on Altra Family")

        events = EventParser.get_events(self.event_file, self.cpu_info)

        set_perf_mux()

        self.core_count = self._get_core_count()
        if self.delay:
            logger.info(f"delaying collection by {self.delay}s...")
            time.sleep(self.delay)

        if self.workload:
            try:
                _ = subprocess.Popen(self.workload, shell=True)
            except Exception as e:
                logger.error(e)

        self._collect_pmu(events)
        progress_bar(self.duration)
        logger.info("Waiting for collectors to complete collection...")
        for pid in self.process_queue:
            logger.debug(f"waiting for process: {pid}")
            os.killpg(os.getpgid(pid), signal.SIGINT)

        run_postprocess(
            self.core_count,
            self.duration,
            self.output,
            self.debug,
            self.plot,
            self.tda,
            self.event_file,
            self.persocket,
            src_path,
        )
        reset_perf_mux()
        change_ownership_recursive(self.output)
        logger.info("Ampere PMU Profiler collection and postprocessing completed")

    def _get_core_count(self):
        if not self.cores:
            result = subprocess.run(
                "lscpu | grep On-line", shell=True, capture_output=True, text=True
            )
            self.cores = result.stdout.split(":")[1].strip()
        count = 0
        for part in self.cores.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                count += end - start + 1
            else:
                count += 1
        logger.info(f"core count: {count}")
        return count

    def _collect_pmu(self, events):
        perf_base = f"perf stat -I {self.interval_ms} -x,"
        if events["core"]:
            core_cmd = f"{perf_base} -C {self.cores} -e {events['core']} -o {self.output}/core_pmu.csv"
            pid = subprocess.Popen(core_cmd, shell=True, preexec_fn=os.setsid).pid
            logger.debug(f"core_pid: {pid}")
            self.process_queue.append(pid)

        if events["cmn"]:
            cmn_cmd = (
                f"{perf_base} -C 0 -e {events['cmn']} -o {self.output}/cmn_pmu.csv"
            )
            pid = subprocess.Popen(cmn_cmd, shell=True, preexec_fn=os.setsid).pid
            logger.debug(f"cmn_proc: {pid}")
            self.process_queue.append(pid)
