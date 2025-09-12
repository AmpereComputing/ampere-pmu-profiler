#!/usr/bin/env python3

###########################################################################
# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause
###########################################################################

import os
import sys
from datetime import datetime
from plotly import graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
import click

report_dir = ""
data_dir = "data"
workload_tag = ""


titles = (
    "<b>Core Frequency</b>",
    "<b>IPC<b>",
    "<b>FrontEnd/BackEnd Stall<b>",
    "<b>Branch MisPrediction<b>",
    "<b>TLB Miss <b>",
    "<b>TLB/Branch MPKI <b>",
    "<b>Cache Miss <b>",
    "<b>Cache MPKI <b>",
    "<b>Memory Bandwidth<b>",
    "<b>CCIX Bandwidth",
)
html_rows = len(titles)


def add_metrics(fig, data, y_title, y_range, row_index, col_index):
    fig.add_trace(data, row=row_index, col=col_index)
    fig.update_yaxes(
        title_text=y_title, range=[0, y_range], row=row_index, col=col_index
    )


def generate_graph(data_dir, report_dir, filepath, metrics_df, workload_tag=None):

    fig = make_subplots(
        rows=html_rows, cols=1, vertical_spacing=0.05, subplot_titles=titles
    )
    # fig = make_subplots(rows=html_rows, cols=1, subplot_titles=titles)

    # filepath = os.path.join(data_dir, "metrics.csv")
    # metrics_df = pd.read_csv(filepath, sep=",")

    # core metrics
    ts = metrics_df["time"]
    freq = go.Scatter(x=ts, y=metrics_df["cpu_freq"], name="Core-Freq")
    ipc = go.Scatter(x=ts, y=metrics_df["IPC"], name="IPC")
    ipc_k = go.Scatter(x=ts, y=metrics_df["IPC_kernel"], name="IPC_kernel")
    br_mis = go.Scatter(
        x=ts, y=metrics_df["branch_mispredict%"], name="Branch MisPrediction"
    )
    dtlb_miss = go.Scatter(x=ts, y=metrics_df["dtlb_walk%"], name="DTLB Walk")
    itlb_miss = go.Scatter(x=ts, y=metrics_df["itlb_walk%"], name="ITLB Walk")
    dtlb_mpki = go.Scatter(x=ts, y=metrics_df["dtlb_mpki"], name="DTLB MPKI")
    itlb_mpki = go.Scatter(x=ts, y=metrics_df["itlb_mpki"], name="ITLB MPKI")
    br_mpki = go.Scatter(x=ts, y=metrics_df["branch_mpki"], name="Branch MPKI")
    l1d_miss = go.Scatter(x=ts, y=metrics_df["l1d_miss%"], name="L1-D Miss%")
    l1i_miss = go.Scatter(x=ts, y=metrics_df["l1i_miss%"], name="L1-I Miss%")
    l2_miss = go.Scatter(x=ts, y=metrics_df["l2_miss%"], name="L2 Miss%")
    l1d_mpki = go.Scatter(x=ts, y=metrics_df["l1d_mpki"], name="L1-D MPKI")
    l1i_mpki = go.Scatter(x=ts, y=metrics_df["l1i_mpki"], name="L1-I MPKI")
    l2_mpki = go.Scatter(x=ts, y=metrics_df["l2_mpki"], name="L2 MPKI")

    dtlb_max = (metrics_df["dtlb_mpki"]).max()
    itlb_max = (metrics_df["itlb_mpki"]).max()
    br_max = (metrics_df["branch_mpki"]).max()
    tlb_max = max(dtlb_max, itlb_max, br_max)

    l1d_max = (metrics_df["l1d_mpki"]).max()
    l1i_max = (metrics_df["l1i_mpki"]).max()
    l2_max = (metrics_df["l2_mpki"]).max()
    c_max = max(l1d_max, l1i_max, l2_max)

    curr_row = 1
    add_metrics(fig, freq, "GHz", 4, curr_row, 1)

    curr_row += 1
    add_metrics(fig, ipc, "IPC", 4, curr_row, 1)
    add_metrics(fig, ipc_k, "IPC", 4, curr_row, 1)

    curr_row += 1
    if set(["frontend_stall%", "backend_stall%"]).issubset(metrics_df.columns):
        front_stall = go.Scatter(
            x=ts, y=metrics_df["frontend_stall%"], name="FrontEndStall"
        )
        back_stall = go.Scatter(
            x=ts, y=metrics_df["backend_stall%"], name="BackEndStall"
        )
        add_metrics(fig, front_stall, "Stall %", 100, curr_row, 1)
        add_metrics(fig, back_stall, "Stall %", 100, curr_row, 1)

    if set(["stall_frontend%", "stall_backend%"]).issubset(metrics_df.columns):
        stall_frontend = go.Scatter(x=ts, y=metrics_df["stall_frontend%"], name="FE")
        stall_frontend_lat = go.Scatter(
            x=ts, y=metrics_df["stall_frontend_lat%"], name="FE_Latency"
        )
        stall_frontend_cache = go.Scatter(
            x=ts, y=metrics_df["stall_frontend_cache%"], name="FE_Cache"
        )
        stall_frontend_tlb = go.Scatter(
            x=ts, y=metrics_df["stall_frontend_tlb%"], name="FE_TLB"
        )
        stall_frontend_flush = go.Scatter(
            x=ts, y=metrics_df["stall_frontend_recovery%"], name="FE_Flush"
        )
        stall_frontend_bob = go.Scatter(
            x=ts, y=metrics_df["stall_fronetend_bob%"], name="FE_BOB"
        )
        stall_backend = go.Scatter(x=ts, y=metrics_df["stall_backend%"], name="BE")
        stall_backend_tlb = go.Scatter(
            x=ts, y=metrics_df["stall_backend_tlb%"], name="BE_TLB"
        )
        stall_backend_l1d = go.Scatter(
            x=ts, y=metrics_df["stall_backend_l1d%"], name="BE_l1d"
        )
        stall_backend_l2d = go.Scatter(
            x=ts, y=metrics_df["stall_backend_l2d%"], name="BE_l2d"
        )
        stall_backend_core = go.Scatter(
            x=ts, y=metrics_df["stall_backend_core%"], name="BE_core"
        )
        stall_backend_res = go.Scatter(
            x=ts, y=metrics_df["stall_backend_res%"], name="BE_Resource"
        )
        stall_backend_rob = go.Scatter(
            x=ts, y=metrics_df["stall_backend_rob%"], name="BE_ROB"
        )
        stall_backend_ixu = go.Scatter(
            x=ts, y=metrics_df["stall_backend_ixu%"], name="BE_IXU"
        )
        stall_backend_fsu = go.Scatter(
            x=ts, y=metrics_df["stall_backend_fsu%"], name="BE_FSU"
        )
        stall_backend_lob = go.Scatter(
            x=ts, y=metrics_df["stall_backend_lob%"], name="BE_LOB"
        )
        stall_backend_sob = go.Scatter(
            x=ts, y=metrics_df["stall_backend_sob%"], name="BE_SOB"
        )

        add_metrics(fig, stall_frontend, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_frontend_lat, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_frontend_cache, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_frontend_tlb, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_frontend_flush, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_frontend_bob, "FrontEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_tlb, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_l1d, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_l2d, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_core, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_res, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_rob, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_ixu, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_fsu, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_lob, "BackEnd %", 100, curr_row, 1)
        add_metrics(fig, stall_backend_sob, "BackEnd %", 100, curr_row, 1)

    curr_row += 1
    add_metrics(fig, br_mis, "Brach Miss %", 100, curr_row, 1)

    curr_row += 1
    add_metrics(fig, dtlb_miss, "TLB Miss %", 100, curr_row, 1)
    add_metrics(fig, itlb_miss, "TLB Miss %", 100, curr_row, 1)

    curr_row += 1
    add_metrics(fig, dtlb_mpki, "MPKI", tlb_max, curr_row, 1)
    add_metrics(fig, itlb_mpki, "MPKI", tlb_max, curr_row, 1)
    add_metrics(fig, br_mpki, "MPKI", tlb_max, curr_row, 1)

    curr_row += 1
    add_metrics(fig, l1d_miss, "Cache Miss %", 100, curr_row, 1)
    add_metrics(fig, l1i_miss, "Cache Miss %", 100, curr_row, 1)
    add_metrics(fig, l2_miss, "Cache Miss %", 100, curr_row, 1)
    if "slc_miss%" in metrics_df.columns:
        slc_miss = go.Scatter(x=ts, y=metrics_df["slc_miss%"], name="SLC Miss%")
        add_metrics(fig, slc_miss, "Cache Miss %", 100, curr_row, 1)

    curr_row += 1
    add_metrics(fig, l1d_mpki, "Cache MPKI", c_max, curr_row, 1)
    add_metrics(fig, l1i_mpki, "Cache MPKI", c_max, curr_row, 1)
    add_metrics(fig, l2_mpki, "Cache MPKI", c_max, curr_row, 1)

    curr_row += 1
    if set(["memrd_bw_GBps", "memwr_bw_GBps"]).issubset(metrics_df.columns):
        memrd_bw = go.Scatter(
            x=ts, y=metrics_df["memrd_bw_GBps"], name="Memory Rd Bandwidth"
        )
        memwr_bw = go.Scatter(
            x=ts, y=metrics_df["memwr_bw_GBps"], name="Memory Wr Bandwidth"
        )
        # max values
        memrd_max = (metrics_df["memrd_bw_GBps"]).max()
        memwr_max = (metrics_df["memwr_bw_GBps"]).max()
        membw_max = max(memrd_max, memwr_max)
        add_metrics(fig, memrd_bw, "GB/s", membw_max, curr_row, 1)
        add_metrics(fig, memwr_bw, "GB/s", membw_max, curr_row, 1)

    curr_row += 1
    if set(["ccix_in_bw_MBps", "ccix_out_bw_MBps"]).issubset(metrics_df.columns):
        ccix_in = go.Scatter(
            x=ts, y=metrics_df["ccix_in_bw_MBps"], name="CCIX In Bandwidth"
        )
        ccix_out = go.Scatter(
            x=ts, y=metrics_df["ccix_out_bw_MBps"], name="CCIX Out Bandwidth"
        )
        # max values
        ccix_in_max = (metrics_df["ccix_in_bw_MBps"]).max()
        ccix_out_max = (metrics_df["ccix_out_bw_MBps"]).max()
        ccix_max = max(ccix_in_max, ccix_out_max)
        add_metrics(fig, ccix_in, "MB/s", ccix_max, curr_row, 1)
        add_metrics(fig, ccix_out, "MB/s", ccix_max, curr_row, 1)

    fig.update_layout(
        title={
            "text": "<b>Ampere PMU Profiler</b>",
            "font": {"color": "#f63823", "size": 18},
        },
        height=1500,
        autosize=True,
        hovermode="x unified",
    )

    report_file = (
        "APP-report-"
        + workload_tag
        + (datetime.now()).strftime("%Y-%m-%d-%H-%M-%S")
        + ".html"
    )
    if report_dir != "":
        report_file = os.path.join(report_dir, report_file)
    fig.write_html(str(report_file), auto_open=False)


@click.command()
@click.option(
    "-d",
    "--data_dir",
    default="data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to input directory/folder containing metrics.csv",
    show_default=True,
)
@click.option("-t", "--tag", type=str, help="workload tag", show_default=False)
def main(data_dir, tag):
    report_dir = data_dir
    if tag:
        workload_tag = tag
    else:
        workload_tag = ""
    try:
        filepath = os.path.join(data_dir, "metrics.csv")
        metrics_df = pd.read_csv(filepath, sep=",")
    except IOError:
        print("No metrics available.")
        sys.exit()
    generate_graph(data_dir, report_dir, filepath, metrics_df, workload_tag)


if __name__ == "__main__":
    main()
