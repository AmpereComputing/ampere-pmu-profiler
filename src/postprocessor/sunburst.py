# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

from yattag import Doc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

doc, tag, text = Doc().tagtext()
metric_parent = {}
metric_level = {}

""" returns sunbursts figure with L1, L2, L3 and L4 TDA """


def get_sunburst(input_csv):
    L1 = "pipeline"
    L2 = ""
    L3 = ""
    try:
        df = pd.read_csv(input_csv, keep_default_na=False, names=["metric", "value"])
    except FileNotFoundError:
        raise SystemExit(f"{input_csv} File not found")

    chars_not_needed = ["_.", "."]

    """ clean and prepare dataframes """
    TDA = df.replace("N/A", np.nan)
    TDA = df[df["metric"].str.endswith(".")]
    TDA.loc[:, "value"] = TDA.value.astype(float)
    TDA.loc[:, "value"] = TDA["value"].apply(lambda x: round(x, 2))

    """ assign parent to each metric """
    for metric in TDA["metric"]:
        if metric == "pipeline":
            metric_parent[metric] = ""
            metric_level[metric] = 0
        if any(
            x in metric.lower()
            for x in ["frontend_.", "backend_.", "retired_.", "lost_."]
        ):
            metric_parent[metric] = "pipeline"
            L1 = metric
            metric_level[metric] = 1
        if metric.count(".") == 2:
            metric_parent[metric] = L1
            metric_level[metric] = 2
            L2 = metric

        if metric.count(".") == 3:
            metric_parent[metric] = L2
            metric_level[metric] = 3
            L3 = metric
        if metric.count(".") == 4:
            metric_parent[metric] = L3
            metric_level[metric] = 4

    """ get parents """
    parent, ignore = get_parents(TDA["metric"].tolist())
    TDA = TDA[~TDA["metric"].isin(ignore)]

    """ get level for each metric """
    levels = get_level(TDA["metric"].tolist())

    """ prepare data with parents and children assigned """
    tda = TDA.copy()
    for item in chars_not_needed:
        tda["metric"] = tda["metric"].str.replace(item, "", regex=False)
    characters = ["pipeline"] + tda["metric"].tolist()
    parent = [""] + parent
    levels.insert(0, 0)  # pipeline is at level 0
    new_data = []
    new_data.insert(0, {"metric": "pipeline", "value": 100})
    TDA = pd.concat([pd.DataFrame(new_data), TDA], ignore_index=True)
    TDA["parent"] = parent
    TDA["id"] = characters
    TDA["level"] = levels
    TDA["description"] = ["Description"] * len(TDA)
    desc = {
        "pipeline": "% total pipeline slots",
        "frontend": "% slots where frontend undersupplies the backend",
        "frontend_latency": "% slots where processor was stalled due to frontend latency issues(cache/TLB); nothing to dispatch",
        "i_cache_miss": "% cycles the processor was stalled due to instruction cache miss",
        "i_tlb_miss": "% cycles the processor was stalled due to instruction TLB miss",
        "recovery": "% cycles the processor was stalled due to flush recovery",
        "bob_full": "% cycles the processor was stalled and backend out-of-order buffer was full(instruction scheduling)",
        "frontend_bw": "% slots the processor didn't dispatch at full bandwidth - able to dispatch partial slots only (1,2 or 3 µops)",
        "backend": "% slots where no µops are delivered due to lack of resources (memory/core)",
        "memory": "% slots the processor was stalled due to backend memory subsystem issues (cache/TLB miss)",
        "d_cache_l1_miss": "% cycles the processor was stalled due to data L1 cache miss",
        "d_tlb_miss": "% cycles the processor was stalled due to data TLB miss",
        "d_cache_l2_miss": "% cycles the processor was stalled due to data L2 cache miss",
        "core": "% slots the processor was stalled due to backend non-memory subsystem issues",
        "resource": "% cycles the processor was stalled due to core resource shortage",
        "rob_full": "% cycles the processor was stalled and reorder buffer was full (out of order instructions waiting to be commited)",
        "ixu_full": "% cycles the processor was stalled and integer execution unit was full (arithmetic and logic ops on integers)",
        "fsu_full": "% cycles the processor was stalled and floating & SIMD unit was full (arithmetic on decimals and SIMD ops)",
        "lob_full": "% cycles the processor was stalled and load-store buffer was full (managing memory read/write ops)",
        "sob_full": "% cycles the processor was stalled and store buffer was full (holding data that needs to be written to memory)",
        "retired": "% slots retiring, (useful work)",
        "pipe_util": "% execute slots utilized",
        "ixu_pipe_util": "% IXU execute slots utilized",
        "fsu_pipe_util": "% FSU execute slots utilized",
        "lost": "% slots wasted due to misspeculation",
        "branch_mispredict": "% slots lost due to branch misprediction",
        "other_clears": "% slots lost due to other/non-branch misspeculation",
    }

    for metric, description in desc.items():
        TDA.loc[TDA["id"] == metric, "description"] = description
    # ensure all values are numeric and greater than 0
    TDA["value"] = pd.to_numeric(TDA["value"], errors="coerce")
    TDA["value"] = TDA["value"].clip(lower=0)
    TDA = realign_metrics(TDA)
    validate_hierarchy(TDA)

    """Create a sunburst plot using Plotly Express"""

    fig = go.Figure()
    fig.add_trace(
        go.Sunburst(
            ids=TDA.id,
            labels=TDA.id,
            parents=TDA.parent,
            values=TDA.value,
            branchvalues="total",
            customdata=TDA["description"],
            hovertemplate="<b>%{label}</b> <br> Value: %{value:.2f}<br>Description: %{customdata}<extra> </extra>",
            textinfo="label+percent entry",
        )
    )
    fig.update_layout(
        # autosize=True,
        # height=900,
        # width=1100,
        margin=dict(t=50, l=25, r=25, b=25)
    )
    return fig


def strip_not_needed(metric_name):
    not_needed = ["_.", "."]
    for char in not_needed:
        metric_name = metric_name.replace(char, "")
    return metric_name


def get_parents(metrics):
    parent = []
    no_parent = []
    for metric in metrics:
        try:
            parent.append(strip_not_needed(metric_parent[metric]))
        except KeyError:
            no_parent.append(metric)
    return parent, no_parent


def get_level(metrics):
    level = []
    for metric in metrics:
        try:
            level.append(metric_level[metric])
        except KeyError:
            print("level cannot be added")
    return level


def realign_metrics(df_orig):
    # make a copy to avoid modifying original dataframe
    df = df_orig.copy()

    # process top to bottom metrics
    for level in sorted(df["level"].unique()):
        # at each level find the children and adjust their values based on their parent
        level_df = df[df["level"] == level]
        for _, row in level_df.iterrows():
            parent_id = row["id"]
            parent_value = row["value"]

            # find the direct children of this parent
            child_idx = df[df["parent"] == parent_id].index
            if len(child_idx) == 0:
                continue
            # original values of children
            child_values = df.loc[child_idx, "value"]
            total_original = child_values.sum()
            if total_original > 0:
                # scale children to match parent while preserving ratios
                df.loc[child_idx, "value"] = (
                    child_values / total_original
                ) * parent_value
            else:
                df.loc[child_idx, "value"] = parent_value / len(child_idx)
    return df


def validate_hierarchy(df):
    levels = sorted(df["level"].unique())
    for lvl in levels:
        parents = df[df["level"] == lvl]
        for _, p in parents.iterrows():
            children = df[df["parent"] == p["id"]]
            child_sum = children["value"].sum()
            if abs(p["value"] - child_sum) > 1e-2 and child_sum != 0:
                print(
                    f"Mismatch: {p['id']}: parent={p['value']} != children sum={child_sum:.2f}"
                )
