# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

import click
from collector.profiler import Profiler
from collector.logger_setup import setup_logger


@click.command()
@click.option("-n", "--duration", type=int, default=100, help="Sample duration (>10s)")
@click.option(
    "-i", "--interval", type=int, default=1, help="sampling interval/frequency (s)"
)
@click.option("-j", "--job", default="", help="workload command to run")
@click.option("-c", "--cores", default="", help="CPU core list")
@click.option("-s", "--persocket", is_flag=True, help="Enable per-socket mode")
@click.option("-p", "--plot", is_flag=True, help="Enable plotting")
@click.option("-o", "--output", default="data", help="Output directory")
@click.option("-e", "--eventfile", default="", help="Eventlist")
@click.option("-t", "--tda", is_flag=True, help="Enable TopDown Accounting")
@click.option("-d", "--debug", is_flag=True, help="Debug mode")
@click.option("-l", "--delay", type=int, default=0, help="Delay PMU collection (s)")
def main(
    duration,
    interval,
    job,
    cores,
    persocket,
    plot,
    output,
    eventfile,
    tda,
    debug,
    delay,
):
    if debug:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    setup_logger(log_level)
    profiler = Profiler(
        duration=duration,
        interval=interval,
        job=job,
        cores=cores,
        persocket=persocket,
        plot=plot,
        output=output,
        event_file=eventfile,
        tda=tda,
        delay=delay,
        debug=debug,
    )
    profiler.run()


if __name__ == "__main__":
    main()
