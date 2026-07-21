# sync_python.py — синхронизация папок в локальной сети на Python

import os
import shutil
import hashlib
import time
import json
import threading
from pathlib import Path
from datetime import datetime
import sys

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

class SyncFolder:
    def __init__(self, source, target, mode='one-way', filters=None, verbose=True):
        self.source = Path(source).resolve()
        self.target = Path(target).resolve()
        self.mode = mode  # 'one-way', 'two-way'
        self.filters = filters or []  # расширения для исключения
        self.verbose = verbose
        self.log_file = "sync.log"
        self.history = []
        self.running = False
        self.observer = None
        self.lock = threading.Lock()

    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_msg = f"{timestamp} - {msg}"
        if self.verbose:
            print(f"📁 {full_msg}")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(full_msg + '\n')

    def should_ignore(self, path):
        """Проверка, нужно ли игнорировать файл/папку"""
        for f in self.filters:
            if f in str(path):
                return True
        # Игнорируем системные папки
        ignore = ['.git', '__pycache__', '.DS_Store', 'Thumbs.db']
        for ig in ignore:
            if ig in str(path):
                return True
        return False

    def get_file_hash(self, filepath):
        """Вычисление хэша файла (MD5)"""
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None

    def file_changed(self, src_path, dst_path):
        """Проверка, изменился ли файл"""
        if not dst_path.exists():
            return True
        if src_path.stat().st_size != dst_path.stat().st_size:
            return True
        if src_path.stat().st_mtime > dst_path.stat().st_mtime:
            return True
        # Сравнение хэшей для надёжности
        src_hash = self.get_file_hash(src_path)
        dst_hash = self.get_file_hash(dst_path)
        return src_hash != dst_hash

    def copy_file(self, src, dst):
        """Копирование файла с созданием папок"""
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.log(f"  + {dst.relative_to(self.target)} (copied)")
            return True
        except Exception as e:
            self.log(f"  ! Ошибка копирования {src}: {e}")
            return False

    def delete_file(self, path):
        """Удаление файла/папки"""
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            self.log(f"  - {path.relative_to(self.target)} (deleted)")
            return True
        except Exception as e:
            self.log(f"  ! Ошибка удаления {path}: {e}")
            return False

    def scan_and_sync(self):
        """Основной метод синхронизации"""
        self.log("Начало синхронизации...")
        if not self.source.exists():
            self.log(f"Ошибка: источник {self.source} не существует")
            return
        self.target.mkdir(parents=True, exist_ok=True)

        changed = 0
        total = 0

        # Сбор информации о файлах в источнике и цели
        src_files = {}
        dst_files = {}

        for path in self.source.rglob('*'):
            if self.should_ignore(path):
                continue
            rel_path = path.relative_to(self.source)
            src_files[rel_path] = path

        if self.target.exists():
            for path in self.target.rglob('*'):
                if self.should_ignore(path):
                    continue
                rel_path = path.relative_to(self.target)
                dst_files[rel_path] = path

        if self.mode == 'one-way':
            # Только из источника в цель
            # Новые/изменённые файлы
            for rel_path, src_path in src_files.items():
                dst_path = self.target / rel_path
                if not dst_path.exists() or self.file_changed(src_path, dst_path):
                    self.copy_file(src_path, dst_path)
                    changed += 1
                total += 1

            # Удалённые в источнике (удаляем в цели)
            for rel_path in dst_files:
                if rel_path not in src_files:
                    dst_path = self.target / rel_path
                    self.delete_file(dst_path)
                    changed += 1

        elif self.mode == 'two-way':
            # Двусторонняя синхронизация (упрощённо: копируем новые/изменённые в обе стороны)
            # Из источника в цель
            for rel_path, src_path in src_files.items():
                dst_path = self.target / rel_path
                if not dst_path.exists() or self.file_changed(src_path, dst_path):
                    self.copy_file(src_path, dst_path)
                    changed += 1
                total += 1

            # Из цели в источник (если файл новее в цели)
            for rel_path, dst_path in dst_files.items():
                src_path = self.source / rel_path
                if not src_path.exists():
                    self.copy_file(dst_path, src_path)
                    changed += 1
                elif self.file_changed(dst_path, src_path):
                    self.copy_file(dst_path, src_path)
                    changed += 1

        self.log(f"Синхронизация завершена (изменено: {changed}, всего: {total})")

    def watch_mode(self):
        """Режим отслеживания изменений (требуется watchdog)"""
        if not WATCHDOG_AVAILABLE:
            self.log("watchdog не установлен. Установите: pip install watchdog")
            return

        class Handler(FileSystemEventHandler):
            def __init__(self, sync_obj):
                self.sync = sync_obj
                self.last_event = time.time()

            def on_modified(self, event):
                if self.sync.should_ignore(event.src_path):
                    return
                # Ограничение частоты
                if time.time() - self.last_event > 2:
                    self.last_event = time.time()
                    self.sync.log("🔔 Обнаружено изменение, запуск синхронизации...")
                    threading.Thread(target=self.sync.scan_and_sync).start()

            def on_created(self, event):
                self.on_modified(event)

            def on_deleted(self, event):
                self.on_modified(event)

        self.log("Запуск режима отслеживания...")
        self.running = True
        event_handler = Handler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.source), recursive=True)
        self.observer.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_watch()

    def stop_watch(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.log("Отслеживание остановлено")

    def run_interactive(self):
        self.log("📁 SyncFolder Pro — Python Edition")
        self.log("Команды: config <source> <target>, sync, watch, status, exit")
        while True:
            cmd = input("> ").strip()
            if cmd == 'exit':
                self.stop_watch()
                break
            elif cmd.startswith('config'):
                parts = cmd.split()
                if len(parts) >= 3:
                    self.source = Path(parts[1]).resolve()
                    self.target = Path(parts[2]).resolve()
                    self.log(f"Источник: {self.source}, Цель: {self.target}")
            elif cmd == 'sync':
                self.scan_and_sync()
            elif cmd == 'watch':
                self.watch_mode()
            elif cmd == 'status':
                self.log(f"Источник: {self.source} (exists: {self.source.exists()})")
                self.log(f"Цель: {self.target} (exists: {self.target.exists()})")
                self.log(f"Режим: {self.mode}")
            else:
                self.log("Неизвестная команда")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        sync = SyncFolder(sys.argv[1], sys.argv[2])
        sync.scan_and_sync()
    else:
        sync = SyncFolder(".", "./sync_target")
        sync.run_interactive()
