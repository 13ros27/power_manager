mod current_monitor;
mod datalogger;
use current_monitor::{CurrentMonitor, CurrentType};
use datalogger::DataLogger;
use std::path::Path;

const CURRENT_TYPES: &[CurrentType; 5] = &[
    CurrentType::Source,
    CurrentType::Drain,
    CurrentType::Drain,
    CurrentType::Unknown,
    CurrentType::Unknown,
];

const NAMES: &[&str; 5] = &["Solar", "House", "HeatPump", "Outside", "Grid"];

fn main() {
    let mut datalogger = DataLogger::new(
        60,
        Path::new("/home/pi/power_manager/data"),
        CURRENT_TYPES,
        NAMES,
    );
    datalogger.tick(&current_monitor::CurrentArray::new([
        current_monitor::Current::new(1.2),
        current_monitor::Current::new(1.0),
        current_monitor::Current::new(9.3),
        current_monitor::Current::new(1.5),
        current_monitor::Current::new(7.6),
    ]));
    datalogger.tick(&current_monitor::CurrentArray::new([
        current_monitor::Current::new(1.2),
        current_monitor::Current::new(1.0),
        current_monitor::Current::new(9.3),
        current_monitor::Current::new(1.5),
        current_monitor::Current::new(7.6),
    ]))
    // let mut cm = CurrentMonitor::default(CURRENT_TYPES).unwrap();
    // datalogger.tick(&cm.read_current().unwrap());
    // let current = cm.read_current().unwrap();
    // println!(
    //     "Current: {:?}, Combined: {}",
    //     current,
    //     current.combine_ignoring(&[3, 4])
    // );
    // datalogger.tick(&cm.read_current().unwrap());
}
