use serial_core::{BaudRate, SerialDevice, SerialPortSettings};
use serial_unix::TTYPort;
use std::fmt::{Display, Formatter};
use std::io;
use std::io::Read;
use std::ops::Deref;
use std::path::Path;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CurrentType {
    Source,
    Drain,
    Unknown, // Defaults to drain
}

impl Display for CurrentType {
    fn fmt(&self, f: &mut Formatter) -> Result<(), std::fmt::Error> {
        write!(
            f,
            "{}",
            match self {
                CurrentType::Source => "Source",
                CurrentType::Drain => "Drain",
                CurrentType::Unknown => "Unknown",
            }
        )
    }
}

#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct Current {
    watts: f64, // Non-negative
}

impl Current {
    pub fn new(watts: f64) -> Self {
        Self { watts }
    }
}

impl Default for Current {
    fn default() -> Self {
        Self { watts: 0. }
    }
}

#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct CurrentArray<const N: usize>([Current; N]);

impl<const N: usize> Deref for CurrentArray<N> {
    type Target = [Current; N];
    fn deref(&self) -> &[Current; N] {
        &self.0
    }
}

impl<const N: usize> CurrentArray<N> {
    pub fn new(currents: [Current; N]) -> Self {
        Self(currents)
    }

    #[allow(dead_code)]
    /// Gives a positive value if the array is producing current, and negative if it is draining current
    pub fn combine(&self, current_types: &[CurrentType; N]) -> isize {
        self.iter()
            .zip(current_types)
            .map(|(p, c_t)| match c_t {
                CurrentType::Source => p.watts as isize,
                CurrentType::Drain => -(p.watts as isize),
                CurrentType::Unknown => -(p.watts as isize),
            })
            .sum()
    }

    pub fn combine_ignoring(&self, current_types: &[CurrentType; N], to_ignore: &[usize]) -> isize {
        self.iter()
            .zip(current_types)
            .enumerate()
            .map(|(i, (p, c_t))| {
                if to_ignore.contains(&i) {
                    0
                } else {
                    match c_t {
                        CurrentType::Source => p.watts as isize,
                        CurrentType::Drain => -(p.watts as isize),
                        CurrentType::Unknown => -(p.watts as isize),
                    }
                }
            })
            .sum()
    }

    pub fn generate_line(&self) -> String {
        let mut line = String::new();
        self.iter()
            .for_each(|p| line.push_str(&format!(",{}", p.watts)));
        line
    }
}

pub struct CurrentMonitor<const N: usize> {
    port: TTYPort,
}

impl<const N: usize> CurrentMonitor<N> {
    pub fn default() -> Result<CurrentMonitor<N>, serial_core::Error> {
        let mut port = TTYPort::open(Path::new("/dev/ttyAMA0"))?;
        let mut settings = port.read_settings()?;
        settings.set_baud_rate(BaudRate::Baud38400)?;
        port.write_settings(&settings)?;
        Ok(CurrentMonitor { port })
    }

    pub fn read_current(&mut self) -> Result<CurrentArray<N>, io::Error> {
        let mut lines = String::new();
        self.port.read_to_string(&mut lines)?;
        let line: Vec<&str> = lines
            .split('\n')
            .last()
            .expect("Error")
            .split(' ')
            .collect();
        if line.len() > 15 {
            let mut currents = [Current::default(); N];
            line[1..N + 1]
                .iter()
                .enumerate()
                .for_each(|(i, p)| currents[i] = Current::new(p.parse::<f64>().unwrap()));
            Ok(CurrentArray::new(currents))
        } else {
            panic!("What happened here: {:?} -- {:?}", lines, line);
        }
    }
}
