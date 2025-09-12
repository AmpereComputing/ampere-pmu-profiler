from test_cli import run_command
from postprocessor.postprocess import main

def test_postprocess():
    result = run_command(["sudo", "postprocess", "--cpus","32","--metric","src/events/events.txt","--duration","10","--output","test_cores/metrics.csv","test_cores/core_pmu.csv"])
    assert "metric averages" in result.stderr
    assert result.returncode == 0

# def test_postprocess(monkeypatch):
#     monkeypatch.setattr("sys.argv", [
#         "postprocess.py",
#         "--cpus", "32",
#         "--metric", "src/events/events.txt",
#         "--duration", "10",
#         "--output", "test_cores/metrics.csv",
#         "test_cores/core_pmu.csv"
#     ])

# main()


