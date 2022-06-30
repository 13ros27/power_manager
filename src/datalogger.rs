use crate::current_monitor::{CurrentArray, CurrentType};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::ops::Deref;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct DataLogger<'a, const N: usize> {
    start_time: Time,
    day_time: u64,
    time_between_logs: u64,
    folder: &'a Path,
    filepath: PathBuf,
    last_logged: Option<u64>,
    day: u64,
    current_types: &'a [CurrentType; N],
    names: &'a [&'a str; N],
}

impl<'a, const N: usize> DataLogger<'a, N> {
    fn create_new_file(
        time: Time,
        folder: &Path,
        current_types: &[CurrentType; N],
        names: &[&str; N],
    ) -> PathBuf {
        if !folder.exists() {
            std::fs::create_dir(folder).unwrap();
        }
        let day = time.get_day();
        let main_filename = format!("D{day}");
        let mut i = 1;
        let path = loop {
            let test_filename = if i == 1 {
                format!("{main_filename}.csv")
            } else {
                format!("{main_filename}_{i}.csv")
            };
            let path = folder.join(&test_filename);
            if !path.exists() {
                break path;
            }
            i += 1;
        };
        let mut file = File::create(&path).expect("Error encountered while creating file!");
        let mut first_line = "Time".to_string();
        for (name, current_type) in names.iter().zip(current_types) {
            first_line.push_str(&format!(",{name} ({current_type})"))
        }
        writeln!(file, "{}", first_line).unwrap();
        path
    }

    pub fn new(
        time_between_logs: u64,
        folder: &'a Path,
        current_types: &'a [CurrentType; N],
        names: &'a [&'a str; N],
    ) -> DataLogger<'a, N> {
        let start_time = Time::new_unix_time();
        DataLogger {
            start_time,
            day_time: start_time.0 % 86400,
            time_between_logs,
            folder,
            filepath: DataLogger::create_new_file(start_time, folder, current_types, names),
            last_logged: None,
            day: start_time.get_day(),
            current_types,
            names,
        }
    }

    pub fn tick(&mut self, current_array: &CurrentArray<N>) {
        let unix = Time::new_unix_time();
        if let Some(t) = self.last_logged {
            if self.start_time < unix && self.day != unix.get_day() {
                self.filepath =
                    DataLogger::create_new_file(unix, self.folder, self.current_types, self.names);
                self.day = unix.get_day();
            }
            if *unix < t + self.time_between_logs {
                return;
            }
        }
        let time = chrono::Utc::now().time();
        let mut file = OpenOptions::new()
            .append(true)
            .open(&self.filepath)
            .unwrap();
        writeln!(
            file,
            "{},{}",
            time.format("T%H%M%SZ"),
            current_array.generate_line()
        )
        .unwrap();
        self.last_logged = Some(*unix);
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
struct Time(u64);

impl Time {
    fn new_unix_time() -> Time {
        Time(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        )
    }

    fn get_day(&self) -> u64 {
        (self.0 as f64 / 86400.).floor() as u64
    }
}

impl Deref for Time {
    type Target = u64;
    fn deref(&self) -> &u64 {
        &self.0
    }
}
