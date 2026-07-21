// sync_cpp.cpp — синхронизация папок в локальной сети на C++

#include <iostream>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <thread>
#include <chrono>
#include <iomanip>
#include <ctime>
#include <sstream>

#ifdef _WIN32
#include <windows.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;

class SyncFolder {
private:
    fs::path source, target;
    std::string mode; // "one-way", "two-way"
    std::vector<std::string> filters;
    bool verbose;
    std::string logFile = "sync.log";

    void log(const std::string& msg) {
        auto now = std::time(nullptr);
        char buf[20];
        std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
        std::string full = std::string(buf) + " - " + msg;
        if (verbose) std::cout << "📁 " << full << std::endl;
        std::ofstream f(logFile, std::ios::app);
        if (f.is_open()) f << full << std::endl;
    }

    bool shouldIgnore(const fs::path& path) {
        std::string p = path.string();
        for (const auto& f : filters) {
            if (p.find(f) != std::string::npos) return true;
        }
        std::vector<std::string> ignore = {".git", "__pycache__", ".DS_Store", "Thumbs.db"};
        for (const auto& ig : ignore) {
            if (p.find(ig) != std::string::npos) return true;
        }
        return false;
    }

    std::string getFileHash(const fs::path& path) {
        std::ifstream file(path, std::ios::binary);
        if (!file.is_open()) return "";
        // Упрощённо: используем размер и время как хэш
        auto size = fs::file_size(path);
        auto mtime = fs::last_write_time(path).time_since_epoch().count();
        std::ostringstream ss;
        ss << size << "_" << mtime;
        return ss.str();
    }

    bool fileChanged(const fs::path& src, const fs::path& dst) {
        if (!fs::exists(dst)) return true;
        if (fs::file_size(src) != fs::file_size(dst)) return true;
        if (fs::last_write_time(src) > fs::last_write_time(dst)) return true;
        return getFileHash(src) != getFileHash(dst);
    }

    bool copyFile(const fs::path& src, const fs::path& dst) {
        try {
            fs::create_directories(dst.parent_path());
            fs::copy(src, dst, fs::copy_options::overwrite_existing);
            log("  + " + dst.string() + " (copied)");
            return true;
        } catch (const std::exception& e) {
            log("  ! Ошибка копирования: " + std::string(e.what()));
            return false;
        }
    }

    bool deleteFile(const fs::path& path) {
        try {
            if (fs::is_directory(path)) {
                fs::remove_all(path);
            } else {
                fs::remove(path);
            }
            log("  - " + path.string() + " (deleted)");
            return true;
        } catch (const std::exception& e) {
            log("  ! Ошибка удаления: " + std::string(e.what()));
            return false;
        }
    }

public:
    SyncFolder(const std::string& src, const std::string& dst,
               const std::string& m = "one-way", bool v = true)
        : source(src), target(dst), mode(m), verbose(v) {}

    void setFilters(const std::vector<std::string>& f) { filters = f; }

    void scanAndSync() {
        log("Начало синхронизации...");
        if (!fs::exists(source)) {
            log("Ошибка: источник не существует");
            return;
        }
        fs::create_directories(target);

        // Сбор файлов
        std::map<std::string, fs::path> srcFiles, dstFiles;
        for (auto& entry : fs::recursive_directory_iterator(source)) {
            if (fs::is_regular_file(entry)) {
                auto rel = fs::relative(entry.path(), source);
                if (!shouldIgnore(rel)) {
                    srcFiles[rel.string()] = entry.path();
                }
            }
        }
        if (fs::exists(target)) {
            for (auto& entry : fs::recursive_directory_iterator(target)) {
                if (fs::is_regular_file(entry)) {
                    auto rel = fs::relative(entry.path(), target);
                    if (!shouldIgnore(rel)) {
                        dstFiles[rel.string()] = entry.path();
                    }
                }
            }
        }

        int changed = 0, total = 0;
        if (mode == "one-way") {
            for (auto& [rel, srcPath] : srcFiles) {
                auto dstPath = target / rel;
                if (!fs::exists(dstPath) || fileChanged(srcPath, dstPath)) {
                    copyFile(srcPath, dstPath);
                    changed++;
                }
                total++;
            }
            for (auto& [rel, dstPath] : dstFiles) {
                if (srcFiles.find(rel) == srcFiles.end()) {
                    deleteFile(dstPath);
                    changed++;
                }
            }
        } else if (mode == "two-way") {
            // Из источника в цель
            for (auto& [rel, srcPath] : srcFiles) {
                auto dstPath = target / rel;
                if (!fs::exists(dstPath) || fileChanged(srcPath, dstPath)) {
                    copyFile(srcPath, dstPath);
                    changed++;
                }
                total++;
            }
            // Из цели в источник
            for (auto& [rel, dstPath] : dstFiles) {
                auto srcPath = source / rel;
                if (!fs::exists(srcPath) || fileChanged(dstPath, srcPath)) {
                    copyFile(dstPath, srcPath);
                    changed++;
                }
            }
        }
        log("Синхронизация завершена (изменено: " + std::to_string(changed) +
            ", всего: " + std::to_string(total) + ")");
    }

    void interactive() {
        log("📁 SyncFolder Pro — C++ Edition");
        log("Команды: config <source> <target>, sync, status, exit");
        std::string cmd;
        while (true) {
            std::cout << "> ";
            std::getline(std::cin, cmd);
            if (cmd == "exit") break;
            else if (cmd.rfind("config", 0) == 0) {
                std::istringstream iss(cmd);
                std::string token, src, dst;
                iss >> token >> src >> dst;
                if (!src.empty() && !dst.empty()) {
                    source = src;
                    target = dst;
                    log("Источник: " + source.string() + ", Цель: " + target.string());
                }
            } else if (cmd == "sync") {
                scanAndSync();
            } else if (cmd == "status") {
                log("Источник: " + source.string() + " (exists: " + std::to_string(fs::exists(source)) + ")");
                log("Цель: " + target.string() + " (exists: " + std::to_string(fs::exists(target)) + ")");
                log("Режим: " + mode);
            } else {
                log("Неизвестная команда");
            }
        }
    }
};

int main(int argc, char* argv[]) {
    SyncFolder sync(".", "./sync_target");
    if (argc >= 3) {
        sync = SyncFolder(argv[1], argv[2]);
        sync.scanAndSync();
    } else {
        sync.interactive();
    }
    return 0;
}
