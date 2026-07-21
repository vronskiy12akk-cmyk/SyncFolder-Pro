📁 SyncFolder Pro — синхронизация папок в локальной сети
Мощный инструмент для синхронизации файлов и папок между компьютерами в локальной сети.
Поддерживает одностороннюю/двустороннюю синхронизацию, контроль версий, фильтры, планировщик и уведомления.
Реализован на 7 языках программирования для демонстрации подходов к работе с файловой системой и сетевыми протоколами.

https://img.shields.io/github/repo-size/yourname/syncfolder
https://img.shields.io/github/stars/yourname/syncfolder?style=social
https://img.shields.io/badge/License-MIT-blue.svg

🧠 Концепция
SyncFolder Pro — это не просто синхронизация. Это интеллектуальный менеджер синхронизации для локальной сети:

✅ Односторонняя синхронизация (source → target).

✅ Двусторонняя синхронизация (обмен изменениями между папками).

✅ Обнаружение изменений — отслеживание новых, изменённых и удалённых файлов.

✅ Фильтры — исключение определённых расширений/папок.

✅ Контроль версий — сохранение предыдущих версий файлов.

✅ Планировщик — автоматическая синхронизация по расписанию или при изменениях.

✅ Уведомления о завершении синхронизации и конфликтах.

✅ Логирование всех действий в файл.

✅ Интерактивный режим (консоль) или простой GUI.

🚀 Как запустить
Для работы с сетью используются системные протоколы (SMB, SSH, NFS) или просто копирование файлов.
В демонстрационных целях используется локальная файловая система или симуляция сети.

bash
# Python (watchdog для отслеживания)
pip install watchdog
python sync_python.py

# C++ (C++17, файловая система)
g++ -std=c++17 -O2 sync_cpp.cpp -o sync && ./sync

# Java (NIO для работы с файлами)
javac sync_java.java && java sync_java

# C# (FileSystemWatcher)
dotnet run   # или csc sync_cs.cs && sync_cs.exe

# Go (fsnotify)
go mod tidy
go run sync_go.go

# Rust (notify crate)
cargo build --release && ./target/release/sync_rs

# JavaScript (Node.js, chokidar)
npm install chokidar
node sync_js.js
🧩 Пример сессии (консольная версия)
text
📁 SyncFolder Pro v2.0
Режимы: one-way, two-way, watch
Доступные команды: sync, watch, status, config, exit

> config source /home/user/docs target /media/backup/docs
Источник: /home/user/docs
Цель: /media/backup/docs

> sync
Начало синхронизации...
Обнаружено изменений: 5
  + file1.txt (new)
  * file2.pdf (modified)
  - file3.jpg (deleted)
Синхронизация завершена (2.3 МБ)

> watch
Запущен режим отслеживания изменений...
(ожидание событий)
📦 Содержимое репозитория
Файл	Язык	Особенности
sync_python.py	Python	+ watchdog для мониторинга, хэш-контроль, планировщик
sync_cpp.cpp	C++	+ std::filesystem, многопоточное копирование, фильтры
sync_java.java	Java	+ WatchService, Recursive copy, конфликт-менеджмент
sync_cs.cs	C#	+ FileSystemWatcher, async copy, версионирование
sync_go.go	Go	+ fsnotify, горутины, цветной вывод
sync_rs.rs	Rust	+ notify, rayon для параллельного копирования, цветной вывод
sync_js.js	JavaScript	+ chokidar, async/await, простое CLI
🔮 Расширенные функции
Двусторонняя синхронизация с разрешением конфликтов (по дате или размеру).

Сжатие перед передачей (опционально).

Интеграция с SSH для удалённой синхронизации.

📜 Лицензия
MIT — свободно используйте, модифицируйте и распространяйте.

🤝 Вклад
Приветствуются пул-реквесты с улучшениями, поддержкой новых платформ и протоколов.

⭐ Если проект помогает вам синхронизировать данные — поставьте звёздочку!
