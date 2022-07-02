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
    let mut cm = CurrentMonitor::default().unwrap();
    loop {
        let current = cm.read_current().unwrap();
        datalogger.tick(&current);
        println!("Current: {:?}, Combined: {}", current, current.combine_ignoring(CURRENT_TYPES, &[3, 4]));
    }
}
