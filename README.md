# Ampere PMU Profiler
[![Build & Testing](https://github.com/AmpereComputing/ampere-pmu-profiler/actions/workflows/ci.yml/badge.svg)](https://github.com/AmpereComputing/ampere-pmu-profiler/actions/workflows/ci.yml) [![License](https://img.shields.io/badge/License-BSD--3-blue)](https://github.com/AmpereComputing/ampere-pmu-profiler/blob/main/LICENSE.txt)


![TDA sunburst plot](/images/mix_sunburst.png)  

Ampere PMU Profiler (APP) is a tool designed to help analyze workload behavior at the microarchitecture (uArch) level. APP is based on the Linux `perf` utility, leveraging Ampere PMU counters to provide key metrics for performance optimization.

## Requirements
- linux perf package
- Python3 and poetry 
```
  sudo apt-get install -y python3 python3-poetry
  poetry install
```
- Root privilege
- Kernel with PMU support or Ampere reference kernel (https://github.com/AmpereComputing/ampere-centos-kernel)

## Usage
```
sudo PYTHONPATH=src python3 -m collector.cli --help

OR

sudo ln -sf $(poetry env info --path)/bin/app /usr/local/bin/app
sudo ln -sf $(poetry env info --path)/bin/postprocess /usr/local/bin/postprocess
sudo app --help

Usage:
-n, --duration [sampling duaration]    : duration of sampling (>10s)
-i, --interval [interval]              : time for each sample(default: 1s)
-j, --job [workload command]           : job or workload command to start(default: none)
-c, --cores [core range]               : cpu core list to collect perf data on(default: all)
-s, --persocket [per socket pmu]       : enable per socket mode
-p, --plot [plot graphs]               : enable plotting
-o, --output [output directory]        : specify the output directory(default: data)
-e, --eventfile [eventlist]            : specify event file(default: events.txt)
-t, --tda [topdown accounting]         : Collect TopDown Accounting metrics and plot TDA graphs
-d, --debug [debug flag]               : enable debug logs
-l, --delay [delayed collection]       : enable delayed PMU collection. default 0s
--help [help]                          : show usage message
```

Example:
```
sudo app -n 10 -i 1 -o example_run --plot
```
The above example creates a 'data' directory consisting of metric csv files and a html report

The collection can be terminated by Ctrl-C <SIGINT>  

If you want to collect the counters in the background, you can seperate the collect and post process in this method:  
```
sudo PYTHONPATH=src python3 -m collector.cli -n 3600 -i 1 -c 0 -o $workload >> collect.log 2>&1 &
profiler_id="$!"

# run the workload

kill -9 $profiler_id
sudo PYTHONPATH=src python3 -m postprocessor.postprocess --cpus <cores> --metric src/events/events_ampereone_ac04.txt --output $workload/metrics.csv $workload/core_pmu.csv $workload/cmn_pmu.csv
```

## Generate report manually
```
sudo PYTHONPATH=src python3 -m postprocessor.plot <data_path> <tag>
```

## TDA
### Example command to collect TDA events and plot graphs
```
sudo app -n 10 -i 1 -c 32-39 -o $workload --tda
```
