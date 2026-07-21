// sync_rs.rs — синхронизация папок в локальной сети на Rust

use std::collections::HashMap;
use std::fs;
use std::io::{self, Write, BufRead};
use std::path::{Path, PathBuf};
use std::time::SystemTime;
use walkdir::WalkDir;
use md5::Md5;
use digest::Digest;
use termion::{color, style};

struct SyncFolder {
    source: PathBuf,
    target: PathBuf,
    mode: String,
    filters: Vec<String>,
    verbose: bool,
    log_file: String,
}

impl SyncFolder {
    fn new(src: &str, dst: &str, mode: &str) -> Self {
        SyncFolder {
            source: PathBuf::from(src),
            target: PathBuf::from(dst),
            mode: mode.to_string(),
            filters: Vec::new(),
            verbose: true,
            log_file: "sync.log".to_string(),
        }
    }

    fn log(&self, msg: &str) {
        let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
        let full = format!("{} - {}", timestamp, msg);
        if self.verbose {
            println!("📁 {}", full);
        }
        let _ = std::fs::OpenOptions::new()
            .append(true)
            .create(true)
            .open(&self.log_file)
            .and_then(|mut f| f.write_all(full.as_bytes()));
    }

    fn should_ignore(&self, path: &Path) -> bool {
        let p = path.to_string_lossy();
        for f in &self.filters {
            if p.contains(f) { return true; }
        }
        let ignore = [".git", "__pycache__", ".DS_Store", "Thumbs.db"];
        for ig in ignore {
            if p.contains(ig) { return true; }
        }
        false
    }

    fn get_file_hash(&self, path: &Path) -> String {
        if let Ok(data) = fs::read(path) {
            let mut hasher = Md5::new();
            hasher.update(&data);
            format!("{:x}", hasher.finalize())
        } else {
            String::new()
        }
    }

    fn file_changed(&self, src: &Path, dst: &Path) -> bool {
        if !dst.exists() { return true; }
        if let (Ok(s_meta), Ok(d_meta)) = (fs::metadata(src), fs::metadata(dst)) {
            if s_meta.len() != d_meta.len() { return true; }
            if let (Ok(s_time), Ok(d_time)) = (s_meta.modified(), d_meta.modified()) {
                if s_time > d_time { return true; }
            }
        }
        self.get_file_hash(src) != self.get_file_hash(dst)
    }

    fn copy_file(&self, src: &Path, dst: &Path) -> bool {
        if let Some(parent) = dst.parent() {
            let _ = fs::create_dir_all(parent);
        }
        match fs::copy(src, dst) {
            Ok(_) => {
                self.log(&format!("  + {} (copied)", dst.file_name().unwrap_or_default().to_string_lossy()));
                true
            }
            Err(e) => {
                self.log(&format!("  ! Ошибка копирования: {}", e));
                false
            }
        }
    }

    fn delete_file(&self, path: &Path) -> bool {
        match fs::remove_dir_all(path) {
            Ok(_) => {
                self.log(&format!("  - {} (deleted)", path.file_name().unwrap_or_default().to_string_lossy()));
                true
            }
            Err(_) => {
                match fs::remove_file(path) {
                    Ok(_) => {
                        self.log(&format!("  - {} (deleted)", path.file_name().unwrap_or_default().to_string_lossy()));
                        true
                    }
                    Err(e) => {
                        self.log(&format!("  ! Ошибка удаления: {}", e));
                        false
                    }
                }
            }
        }
    }

    fn get_files(&self, dir: &Path) -> Vec<PathBuf> {
        let mut files = Vec::new();
        if !dir.exists() { return files; }
        for entry in WalkDir::new(dir).into_iter().filter_map(|e| e.ok()) {
            if entry.file_type().is_file() {
                let path = entry.path().to_path_buf();
                if !self.should_ignore(&path) {
                    files.push(path);
                }
            }
        }
        files
    }

    fn scan_and_sync(&self) {
        self.log("Начало синхронизации...");
        if !self.source.exists() {
            self.log("Ошибка: источник не существует");
            return;
        }
        let _ = fs::create_dir_all(&self.target);

        let src_files = self.get_files(&self.source);
        let dst_files = self.get_files(&self.target);

        let mut changed = 0;
        let total = src_files.len();

        if self.mode == "one-way" {
            for src_path in &src_files {
                if let Ok(rel) = src_path.strip_prefix(&self.source) {
                    let dst_path = self.target.join(rel);
                    if !dst_path.exists() || self.file_changed(src_path, &dst_path) {
                        self.copy_file(src_path, &dst_path);
                        changed += 1;
                    }
                }
            }
            for dst_path in &dst_files {
                if let Ok(rel) = dst_path.strip_prefix(&self.target) {
                    let src_path = self.source.join(rel);
                    if !src_path.exists() {
                        self.delete_file(dst_path);
                        changed += 1;
                    }
                }
            }
        } else if self.mode == "two-way" {
            for src_path in &src_files {
                if let Ok(rel) = src_path.strip_prefix(&self.source) {
                    let dst_path = self.target.join(rel);
                    if !dst_path.exists() || self.file_changed(src_path, &dst_path) {
                        self.copy_file(src_path, &dst_path);
                        changed += 1;
                    }
                }
            }
            for dst_path in &dst_files {
                if let Ok(rel) = dst_path.strip_prefix(&self.target) {
                    let src_path = self.source.join(rel);
                    if !src_path.exists() || self.file_changed(dst_path, &src_path) {
                        self.copy_file(dst_path, &src_path);
                        changed += 1;
                    }
                }
            }
        }
        self.log(&format!("Синхронизация завершена (изменено: {}, всего: {})", changed, total));
    }

    fn interactive(&mut self) {
        self.log("📁 SyncFolder Pro — Rust Edition");
        println!("{}Команды{}: config <source> <target>, sync, status, exit", color::Fg(color::Yellow), style::Reset);
        let stdin = io::stdin();
        let mut reader = stdin.lock();
        loop {
            print!("{}> {} ", color::Fg(color::Cyan), style::Reset);
            io::stdout().flush().unwrap();
            let mut line = String::new();
            if reader.read_line(&mut line).is_err() { break; }
            let line = line.trim();
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.is_empty() { continue; }
            match parts[0] {
                "exit" => break,
                "config" => {
                    if parts.len() >= 3 {
                        self.source = PathBuf::from(parts[1]);
                        self.target = PathBuf::from(parts[2]);
                        self.log(&format!("Источник: {}, Цель: {}", self.source.display(), self.target.display()));
                    }
                }
                "sync" => self.scan_and_sync(),
                "status" => {
                    self.log(&format!("Источник: {} (exists: {})", self.source.display(), self.source.exists()));
                    self.log(&format!("Цель: {} (exists: {})", self.target.display(), self.target.exists()));
                    self.log(&format!("Режим: {}", self.mode));
                }
                _ => self.log("Неизвестная команда"),
            }
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut sync = SyncFolder::new(".", "./sync_target", "one-way");
    if args.len() >= 3 {
        sync = SyncFolder::new(&args[1], &args[2], "one-way");
        sync.scan_and_sync();
    } else {
        sync.interactive();
    }
}
