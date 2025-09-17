# Copyright (c) 2025, Ampere Computing LLC.
#
# SPDX-License-Identifier: BSD-3-Clause

from click.testing import CliRunner
from postprocessor import tda

from test_cli import run_command

def test_cli_tda():
    result = run_command(["sudo", "app", "-n", "10", "-i", "1", "-o", "tda", "--tda"])
    assert "static HTML file written" in result.stderr
    assert result.returncode == 0

def test_tda_sunburst():
    # result = run_command(["poetry", "run", "sudo", "python3", "src/postprocessor/tda.py", "-i", "tda"])
    result = CliRunner().invoke(tda.main, ["-i", "tda"])
    # assert "static HTML file written" in result.output
    assert result.exit_code == 0

def test_tda_icicle():
    # result = run_command(["poetry", "run", "sudo", "python3", "src/postprocessor/tda.py", "-i", "tda", "-t", "icicle"])
    result = CliRunner().invoke(tda.main, ["-i", "tda", "-t", "icicle"])
    assert result.exit_code == 0

