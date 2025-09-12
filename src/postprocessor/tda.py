# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

from postprocessor import icicle
from postprocessor import sunburst
import os
from postprocessor.postprocess import setup_logger
import click

logger = setup_logger()


def write_html(res_dir, base_input_file, html_report_out, chart_type):
    try:
        tda_inp = base_input_file.split(".")[0] + ".average.csv"
        tda_inp = os.path.join(res_dir, tda_inp)
        from yattag import Doc, indent

        doc, tag, text = Doc().tagtext()
        with tag("html"):
            with tag("style"):
                text("h1{text-align: center;background-color: #FF817E;}")
                # text("h2{text-align: center;background-color: #FFCCCB;}")
            #     text('.navbar {background-color: #333;overflow: hidden;position: fixed;bottom: 0;width: 100%;}')
            #     text('.navbar a {float: left;display: block;color: #f2f2f2;text-align: center;padding: 14px 16px;text-decoration: none;font-size: 17px;}')
            #     text('.navbar a:hover {background-color: #ddd;color: black;}')
            #     text('.navbar a.active {background-color: #04AA6D;color: white;}')
            # text('input{position: fixed;}')

            with tag("head"):
                doc.asis(
                    '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
                )
                with tag("h1"):
                    text("Ampere® PMU Profiler")
            with tag("body"):
                if chart_type == "icicle":
                    fig1 = icicle.get_icicle(tda_inp)
                else:
                    fig1 = sunburst.get_sunburst(tda_inp)
                with tag("h2", align="center"):
                    text("Top Down  Accounting (TDA)")
                with doc.tag("div"):
                    doc.attr(id="tda")
                    doc.asis(fig1.to_html(full_html=False, include_plotlyjs="cdn"))
                    # doc.asis(fig1)

        result = indent(doc.getvalue())
        if "/" in html_report_out:
            html_report_out = html_report_out.rpartition("/")[-1]
        out_html = os.path.join(res_dir, html_report_out)
        with open(out_html, "w") as file:
            file.write(result)
        logger.info(f"static HTML file written at {out_html}")
    except Exception as e:
        logger.error(e)


@click.command()
@click.option(
    "-i",
    "--input_dir",
    default="data",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to input directory/folder containing metrics.csv",
    show_default=True,
)
@click.option(
    "-t",
    "--chart_type",
    default="sunburst",
    type=click.Choice(["sunburst", "icicle"], case_sensitive=False),
    help="Type of TDA chart to generate.",
    show_default=True,
)
def main(input_dir, chart_type):
    write_html(input_dir, "metrics.csv", "tda.html", chart_type)


if __name__ == "__main__":
    main()
