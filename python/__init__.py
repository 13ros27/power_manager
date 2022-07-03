"""Datalogs the current readings."""
from current import CurrentMonitor, CurrentType
from datalogger import DataLogger
from pathlib import Path


NAMES = ['Solar', 'House', 'HeatPump', 'Outside', 'Grid']
CURRENT_TYPES = [
    CurrentType.Source,
    CurrentType.Drain,
    CurrentType.Drain,
    CurrentType.Unknown,
    CurrentType.Unknown,
]

if __name__ == '__main__':
    data_logger = DataLogger(15, Path('/home/pi/power_manager/data'), NAMES,
                             CURRENT_TYPES)
    current_monitor = CurrentMonitor(len(NAMES))

    while True:
        currents = current_monitor.read()
        print(currents)
        data_logger.tick(currents)
