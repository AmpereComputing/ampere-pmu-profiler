import subprocess
import os
import re
import shutil
import platform
import pytest

def run_command(cmd):
    res = subprocess.run(
        cmd, capture_output=True, text=True,
    )
    return res

def ensure_stress_ng_installed():
    if shutil.which("stress-ng"):
        return
    distro = platform.linux_distribution()[0].lower() if hasattr(platform, "linux_distribution") else platform.system().lower()
    try:
        if "ubuntu" in distro or "debian" in distro:
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "stress-ng"], check=True)
        elif "fedora" in distro or "redhat" in distro or "centos" in distro:
            subprocess.run(["sudo", "dnf", "install", "-y", "stress-ng"], check=True)
        elif "arch" in distro:
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "stress-ng"], check=True)
        else:
            raise RuntimeError(f"unsupported OS for stress-ng installation: {distro}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install stress-ng: {e}")

@pytest.fixture(scope="session", autouse=True)
def setup_stress_ng():
    ensure_stress_ng_installed()

def test_cli_help(script_runner):
    #assumes `poetry install` is run
    result = script_runner.run(["app", "--help"])
    assert result.success
    assert "Usage:" in result.stdout
    assert "--job" in result.stdout
    assert "--duration" in result.stdout

def test_cli_duration5():
    result = run_command(["sudo", "app", "-n", "5"])
    assert "ValueError: Sample duration must be >= 10 seconds" in result.stderr
    assert result.returncode == 1

def test_cli_duration10():
    result = run_command(["sudo", "app", "-n", "10"])
    assert "Ampere PMU Profiler collection and postprocessing completed" in result.stderr
    assert result.returncode == 0

def test_cli_workload():
    result = run_command(["sudo", "app", "-n", "10", "-j", "stress-ng -c 0 -t 20"])
    assert "Ampere PMU Profiler collection and postprocessing completed" in result.stderr
    assert result.returncode == 0

def test_cli_generic_eventlist():
    result = run_command(["sudo", "app", "-n", "10", "-e", "src/events/events.txt"])
    assert "Ampere PMU Profiler collection and postprocessing completed" in result.stderr
    assert result.returncode == 0

def test_cli_wrong_eventlist():
    result = run_command(["sudo", "app", "-e", "wronglist.txt"])
    assert "FileNotFoundError" in result.stderr
    assert result.returncode != 0


def test_cli_cores():
    result = run_command(["sudo", "app", "-n", "10", "-i", "1", "-c", "0-31", "-o", "test_cores", "-e", "src/events/events.txt"])
    assert "Ampere PMU Profiler collection and postprocessing completed" in result.stderr
    assert result.returncode == 0

def test_cli_persocket():
    result = run_command(["sudo", "app", "-n", "10", "-i", "1", "-s"])
    assert "Ampere PMU Profiler collection and postprocessing completed" in result.stderr
    assert result.returncode == 0

def test_cli_delayed():
    result = run_command(["sudo", "app", "-n", "10", "-i", "1", "--delay", "3"])
    assert "delaying collection" in result.stderr
    assert result.returncode == 0
         
