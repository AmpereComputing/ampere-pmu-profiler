#!/usr/bin/env python3

###########################################################################
# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause
###########################################################################


from collections import OrderedDict
from collections import Counter
from typing import NamedTuple
import sys
import os
import re
import csv
import string
import click
from collector.logger_setup import setup_logger

eventname: list[str] = []
constdict = {
    "const_cpus": 80,
    "const_sampletime": 1.0,
    "const_width": 4,
    "const_ixu_exec_width": 4,
    "const_fsu_exec_width": 2,
    "const_wall_clock_time": 0,
}
metricfile = "events.txt"


class EventInfo(NamedTuple):
    name: str
    code: str
    groupid: int


# get the PMU names from metric expression
def get_metric_events(formula):
    f_len = len(formula)
    start = 0
    metric_events = []
    while start < f_len:
        s_idx = formula.find("[", start)
        e_idx = formula.find("]", start)
        if s_idx != -1 and e_idx != -1:
            metric_events.append(formula[s_idx + 1 : e_idx])
        else:
            break
        start = e_idx + 1
    return metric_events


def get_expression_socket(expr, socket):
    f_len = len(expr)
    start = 0
    expr_new = expr
    while start < f_len:
        s_idx = expr.find("[", start)
        e_idx = expr.find("]", start)
        if s_idx != -1 and e_idx != -1:
            event_all = expr[s_idx : e_idx + 1]  # event with the []: [cycles]
            event = expr[s_idx + 1 : e_idx]  # event without []: cycles
            event_s = "[" + socket + event + "]"  # event with socket: s0.cycles
            if event.startswith("const"):  # bypass the const replacement
                break
            expr_new = expr_new.replace(event_all, event_s)  # [cycles] ==> [s0.cycles]
        else:
            break
        start = e_idx + 1
    # print(expr, "==>", expr_new)
    return expr_new


def get_event_index(event, mapping, winnerID):
    offset = 0
    i = 0
    while i < winnerID:
        offset += len(mapping[i])
        i += 1
    grpindx = mapping[winnerID].index(event)
    return offset + grpindx


def most_frequent_group(grplist):
    all_grpid = [num for sublist in grplist for num in sublist]
    counter = Counter(all_grpid)
    max_count = max(counter.values(), default=0)
    return min(num for num, count in counter.items() if count == max_count)


def get_groupid(event, eventmapping):
    group_id = []  # if present in multiple groups
    for grpid, events in eventmapping.items():
        if event in events:
            group_id.append(grpid)
    return group_id


# evaluate formula or expression
def evaluate_expression(expr, rawdata, event_mapping):
    global eventname
    tmp_expr = expr
    metric_events = get_metric_events(expr)
    expr = expr.replace("[", "")
    expr = expr.replace("]", "")

    # assign consts in the expression and create a list for collected events
    collected_events = []
    for event in metric_events:
        if event in constdict:
            expr = expr.replace(event, str(constdict[event]))
        else:
            # replace :, - with _ . workaround needed for substring replacement in expr
            tmp_event = event
            event = event.replace("-", "_")
            event = event.replace(":", "_")
            expr = expr.replace(tmp_event, event)
            collected_events.append(event)
    logger.debug("collected events %s", collected_events)
    grps = []
    event_in_multiple_groups = []
    for event in collected_events:
        event_grp_list = get_groupid(event, event_mapping)
        grps.append(event_grp_list)
        if len(event_grp_list) > 1 and event not in event_in_multiple_groups:
            event_in_multiple_groups.append(event)
        logger.debug("event: %s event_grp_list %s", event, event_grp_list)
    if any(grp for grp in grps):
        winnerid = most_frequent_group(grps)
        logger.debug("Winner %s", winnerid)
        logger.debug("event in multiple groups %s", event_in_multiple_groups)

    for i, event in enumerate(eventname):
        event = event.replace("-", "_")
        event = event.replace(":", "_")
        if event in collected_events and event in event_in_multiple_groups:
            idx = get_event_index(event, event_mapping, winnerid)
            logger.debug(
                "idx:event:rawdata:expr-> %s:%s:%s:%s",
                idx,
                event,
                rawdata[idx + 1],
                expr,
            )
            expr = re.sub(
                r"\b" + event + r"\b", str(rawdata[idx + 1]), expr
            )  # +1 for time
            collected_events.remove(event)  # remove event after it has been visited
        elif event in collected_events:
            logger.debug(
                "i:event:rawdata:expr-> %s:%s:%s:%s", i, event, rawdata[i + 1], expr
            )
            expr = re.sub(
                r"\b" + event + r"\b", str(rawdata[i + 1]), expr
            )  # +1 for time
            collected_events.remove(event)  # remove event after it has been visited

    result = ""
    try:
        result = str("{:.4f}".format(eval(expr)))
    except ZeroDivisionError:
        logger.error("Divide by Zero evaluating %s", tmp_expr)
        result = "0"
        pass
    except SyntaxError:
        logger.error("Syntax error evaluating %s", expr)
        logger.error(tmp_expr)
        result = ""
        pass
    except Exception:
        logger.exception("Unknown error evaluating %s  %s", tmp_expr, expr)
        result = ""

    return result


def get_compatiable_event(e):
    tmp = e
    if e.endswith("_k"):
        tmp = e[:-2] + ":k"
    else:
        tmp = e.replace("_", "-")
    return tmp


# generate metrics from raw counters
def loadmetrics(infile, outfile, cores, persocket):
    global eventname
    global metricfile
    start = False
    uncore_metrics = False
    metrics = []
    metrics_s1 = []
    event_mapping, event_list = get_event_mappings()
    logger.debug("infile: %s, outfile: %s", infile, outfile)
    logger.debug("eventname: %s", eventname)

    with open(metricfile, "r") as f_metric:
        for row in f_metric:
            if row.startswith(";"):
                start = True
                continue
            if not start:
                continue

            if "uncore_metrics" in row:  # uncore_metrics doenn't support persocket mode
                logger.debug("found uncore events")
                uncore_metrics = True

            if not row.strip() or row.startswith("#"):
                continue

            if persocket and not uncore_metrics:
                check = 2
            else:
                check = 1

            temp = row.split("=")
            metric = temp[0].strip()
            expression = temp[1].strip()

            add_metric = True
            metric_tmp = metric
            socket = ""

            for c in range(check):
                if persocket and not uncore_metrics:
                    socket = "s0." if c == 0 else "s1."
                expression_new = get_expression_socket(expression, socket)
                metric_events = get_metric_events(expression_new)
                logger.debug("expression_new: %s", expression_new)
                for e in metric_events:
                    if e.startswith("const"):
                        continue
                    if e not in eventname:
                        if get_compatiable_event(e) not in eventname:
                            logger.debug("Skipping event: %s", e)
                            add_metric = False

                if add_metric and persocket:
                    metric_tmp = socket + metric
                if c == 0:
                    metrics.append({"name": metric_tmp, "expression": expression_new})
                    # logger.debug("%s : %s",c,metrics)
                if c == 1:
                    metrics_s1.append(
                        {"name": metric_tmp, "expression": expression_new}
                    )

    f_metric.close()

    constdict["const_cpus"] = cores

    metricrow = []
    if persocket:
        metrics.extend(metrics_s1)
    for m in metrics:
        metricrow.append(m["name"])

    fout = open(outfile, "w")
    outcsv = csv.writer(fout, dialect="excel")

    fin = open(infile, "r")
    incsv = csv.reader(fin, delimiter=",")

    rowcount = 0
    timestamp = 0.00
    for row in incsv:
        outrow = []
        mval = [""] * len(metricrow)
        if not row:
            continue
        if rowcount > 0:
            interval = float(row[0]) - timestamp
            timestamp = float(row[0])
            constdict["const_sampletime"] = interval

            for m in metrics:
                idx = metricrow.index(m["name"])
                result = evaluate_expression(m["expression"], row, event_mapping)
                mval[idx] = result
            outrow.append(row[0])
            outrow.extend(mval)
            rawdata = row[1:]
            for i, r in enumerate(rawdata):
                try:
                    rawdata[i] = str((round(float(r))))
                except Exception:
                    rawdata[i] = ""

            outrow.extend(rawdata)
        else:
            outrow.append(row[0])
            outrow.extend(metricrow)
            outrow.extend(row[1:])
        outcsv.writerow(outrow)
        rowcount = rowcount + 1


# get event to rNNN mapping
def get_event_mappings():
    event_mapping = OrderedDict()
    event_list = []
    group_id = 0
    with open(metricfile, "r") as f_event:
        for row in f_event:
            if not row.strip() or row.startswith("#"):
                continue
            new_group = False
            if row.startswith(";"):
                break
            if row.startswith("}"):
                new_group = True
                logger.debug("new group with id: %s", group_id)

            row = row.strip()
            if "|" in row:
                event = row.split("|")
                name = event[0].strip()
                code = event[1].strip()
                event_list.append(EventInfo(name=name, code=code, groupid=group_id))
                name = name.replace(":", "_")
                name = name.replace("-", "_")
                if event_mapping.get(group_id) is None:
                    event_mapping.setdefault(group_id, [name])
                else:
                    event_mapping[group_id].append(name)
            if new_group:
                group_id += 1
    return event_mapping, event_list


# process raw pmu counters, transpose the data with one raw for each timestamp
def process_stats(infile, persocket, outfile):
    logger.debug("processing stats with %s input and output %s", infile, outfile)
    global eventname
    prev_time = 0.00
    first_out_row = True
    rowdata = []
    row0data = []
    socket = []
    _, event_list = get_event_mappings()
    logger.debug(
        "events in eventlist: %s", ", ".join(str(events) for events in event_list)
    )

    fout = open(outfile, "w")
    outcsv = csv.writer(fout, delimiter=",")
    index = 0
    with open(infile, "r") as fin:
        incsv = csv.reader(fin, delimiter=",")
        row0data.append("time")
        for it, row in enumerate(incsv):
            if it == 0:
                continue
            if not row:
                continue

            s = ""
            if persocket:
                s = row[1].strip()
                if not socket:
                    socket.append(s)
                elif s and s not in socket:
                    socket.append(s)
                stat = row[5].strip()
                val = row[3].strip()

            else:
                stat = row[3].strip()
                val = row[1].strip()

            if not stat or not val:
                continue

            # check if any collected event is rNNN format and replace with the name
            if stat.startswith("r"):
                code = stat[1:]
                if all(c in string.hexdigits for c in code):
                    name = event_list[index].name
                    stat = name
            try:
                time = round(float(row[0].strip()), 2)
            except (ValueError, IndexError):
                continue

            if prev_time != time:
                if len(rowdata) > 0 and first_out_row:
                    first_out_row = False
                    outcsv.writerow(row0data)
                    eventname.extend(row0data[1:])

                if not first_out_row:
                    outcsv.writerow(rowdata)
                rowdata = []
                rowdata.append(time)
                index = 0

            if first_out_row:
                if not persocket:
                    row0data.append(stat)
                else:
                    row0data.append("s" + str(socket.index(s)) + "." + stat)

            index = index + 1
            try:
                rowdata.append(float(val))
            except Exception:
                # for some cases, "not counted" or "not supported" will be captured:
                # 1.670835594,<not counted>,,r31,0,100.00,,
                # 1.670835594,<not supported>,,bus_access,0,100.00,,
                # append a 0 instead of an empty string can aovid the error:
                # ValueError: could not convert string to float: ''
                rowdata.append(float(0))

            prev_time = time
    fin.close()
    fout.close()


def join_files(n, outdir, outfile):
    # assume intermediate files are named tmp0.csv, tmp1.csv so on
    fout = open(outfile, "w")
    outcsv = csv.writer(fout, delimiter=",")
    incsvs = []
    lines = sys.maxsize
    for i in range(n):
        fin = open(os.path.join(outdir, "tmp" + str(i) + ".csv"), "r")
        csvreader = csv.reader(fin, delimiter=",")
        current_line_count = len(list(csvreader))
        if current_line_count < lines:
            lines = current_line_count
        fin.close()

    for i in range(n):
        fin = open(os.path.join(outdir, "tmp" + str(i) + ".csv"), "r")
        incsvs.append(csv.reader(fin, delimiter=","))

    count = 0
    for row in incsvs[0]:
        if count >= lines:
            break
        outrow = []
        outrow.extend(row)
        for i in range(1, n):
            extrow = next(incsvs[i])
            outrow.extend(extrow[1:])
        outcsv.writerow(outrow)
        count += 1


def get_averages(infile, resdir):
    fin = open(infile, "r")
    incsv = csv.reader(fin, delimiter=",")
    # outfile = (infile.split('.'))[0]+".average.csv"
    outfile = os.path.join(resdir, "metrics.average.csv")
    fout = open(outfile, "w")
    outcsv = csv.writer(fout, delimiter=",")

    numlines = 0.0
    header = []
    sumrow = []
    for row in incsv:
        if not row:
            continue

        if numlines == 0:
            header = row[1:]
            sumrow = [0.0] * (len(header))
            numlines = numlines + 1
            continue
        for i, r in enumerate(row):
            if i == 0:
                continue
            sumrow[i - 1] = sumrow[i - 1] + float(r)
        numlines = numlines + 1

    numlines = numlines - 1
    logger.info("number of samples: %d" % numlines)
    for i, h in enumerate(header):
        outcsv.writerow([h, str("{:,.4f}".format(sumrow[i] / numlines))])
    logger.info("metric averages: %s", outfile)


def clean_temp_files(tmp, files, resdir):
    os.remove(tmp)
    for i, f in enumerate(files):
        tmpfile = os.path.join(resdir, f"tmp{i}.csv")
        if os.path.exists(tmpfile):
            os.remove(tmpfile)


@click.command()
@click.argument("files", nargs=-1, type=click.Path())
@click.option("--output", required=True, type=click.Path(), help="output csv files")
@click.option("--persocket", is_flag=True, help="enable per-socket processing")
@click.option("--cpus", type=int, help="number of CPU cores")
@click.option("--metric", type=click.Path(), help="metricfile/eventlist")
@click.option("--debug", is_flag=True, help="enable debug messages")
@click.option("--duration", help="sampling duration")
def main(files, output, persocket, cpus, metric, debug, duration):
    global metricfile, logger
    loglevel = "debug" if debug else "info"
    logger = setup_logger(loglevel.upper(), "app_postprocess.log")
    logger.info("Started Ampere PMU Profiler processing")
    resdir = os.path.dirname(output)
    tmpout = os.path.join(resdir, "tmp.csv")
    metricfile = metric if metric else "events.txt"
    logger.info("eventfile used: " + metricfile)
    logger.info("results directory: " + resdir)
    count = 0
    for i, f in enumerate(files):
        if not os.path.isfile(f):
            continue
        tmpfile = os.path.join(resdir, f"tmp{i}.csv")
        is_persocket = (
            persocket and "core_pmu" in f
        )  # only core pmu support persocket mode
        logger.debug("Persocket: " + str(is_persocket))
        process_stats(f, is_persocket, tmpfile)
        count += 1
    if count > 1:
        logger.debug("joining tmp files")
        join_files(count, resdir, tmpout)
    else:
        tmpout = os.path.join(resdir, "tmp0.csv")
    cores = cpus if cpus else 80
    constdict["const_cpus"] = cores
    constdict["const_wall_clock_time"] = duration
    logger.info("cores: " + str(cores))
    logger.debug("generate metrics from raw counters")
    loadmetrics(tmpout, output, cores, persocket)
    if not debug:
        clean_temp_files(tmpout, files, resdir)
    logger.debug("constants: %s", constdict)
    get_averages(output, resdir)


if __name__ == "__main__":
    main()
