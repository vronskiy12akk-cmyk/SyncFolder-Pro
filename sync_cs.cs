// sync_cs.cs — синхронизация папок в локальной сети на C#

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Threading;

class SyncFolder
{
    private string source, target;
    private string mode; // "one-way", "two-way"
    private List<string> filters = new List<string>();
    private bool verbose = true;
    private string logFile = "sync.log";
    private FileSystemWatcher watcher;
    private bool running = true;

    public SyncFolder(string src, string dst, string m = "one-way")
    {
        source = src;
        target = dst;
        mode = m;
    }

    private void Log(string msg)
    {
        string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        string full = $"{timestamp} - {msg}";
        if (verbose) Console.WriteLine($"📁 {full}");
        File.AppendAllText(logFile, full + "\n");
    }

    private bool ShouldIgnore(string path)
    {
        foreach (var f in filters)
            if (path.Contains(f)) return true;
        string[] ignore = { ".git", "__pycache__", ".DS_Store", "Thumbs.db" };
        foreach (var ig in ignore)
            if (path.Contains(ig)) return true;
        return false;
    }

    private string GetFileHash(string path)
    {
        try
        {
            using var md5 = MD5.Create();
            using var stream = File.OpenRead(path);
            byte[] hash = md5.ComputeHash(stream);
            return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
        }
        catch { return ""; }
    }

    private bool FileChanged(string src, string dst)
    {
        if (!File.Exists(dst)) return true;
        var srcInfo = new FileInfo(src);
        var dstInfo = new FileInfo(dst);
        if (srcInfo.Length != dstInfo.Length) return true;
        if (srcInfo.LastWriteTime > dstInfo.LastWriteTime) return true;
        return GetFileHash(src) != GetFileHash(dst);
    }

    private bool CopyFile(string src, string dst)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(dst));
            File.Copy(src, dst, true);
            Log($"  + {Path.GetFileName(dst)} (copied)");
            return true;
        }
        catch (Exception e)
        {
            Log($"  ! Ошибка копирования: {e.Message}");
            return false;
        }
    }

    private bool DeleteFile(string path)
    {
        try
        {
            if (Directory.Exists(path))
                Directory.Delete(path, true);
            else if (File.Exists(path))
                File.Delete(path);
            Log($"  - {Path.GetFileName(path)} (deleted)");
            return true;
        }
        catch (Exception e)
        {
            Log($"  ! Ошибка удаления: {e.Message}");
            return false;
        }
    }

    private List<string> GetFiles(string dir)
    {
        var files = new List<string>();
        if (!Directory.Exists(dir)) return files;
        foreach (var file in Directory.GetFiles(dir, "*", SearchOption.AllDirectories))
        {
            if (!ShouldIgnore(file))
                files.Add(file);
        }
        return files;
    }

    public void ScanAndSync()
    {
        Log("Начало синхронизации...");
        if (!Directory.Exists(source))
        {
            Log("Ошибка: источник не существует");
            return;
        }
        Directory.CreateDirectory(target);

        var srcFiles = GetFiles(source);
        var dstFiles = GetFiles(target);

        int changed = 0, total = srcFiles.Count;

        if (mode == "one-way")
        {
            foreach (var srcPath in srcFiles)
            {
                var rel = Path.GetRelativePath(source, srcPath);
                var dstPath = Path.Combine(target, rel);
                if (!File.Exists(dstPath) || FileChanged(srcPath, dstPath))
                {
                    CopyFile(srcPath, dstPath);
                    changed++;
                }
            }
            foreach (var dstPath in dstFiles)
            {
                var rel = Path.GetRelativePath(target, dstPath);
                var srcPath = Path.Combine(source, rel);
                if (!File.Exists(srcPath))
                {
                    DeleteFile(dstPath);
                    changed++;
                }
            }
        }
        else if (mode == "two-way")
        {
            // Из источника в цель
            foreach (var srcPath in srcFiles)
            {
                var rel = Path.GetRelativePath(source, srcPath);
                var dstPath = Path.Combine(target, rel);
                if (!File.Exists(dstPath) || FileChanged(srcPath, dstPath))
                {
                    CopyFile(srcPath, dstPath);
                    changed++;
                }
            }
            // Из цели в источник
            foreach (var dstPath in dstFiles)
            {
                var rel = Path.GetRelativePath(target, dstPath);
                var srcPath = Path.Combine(source, rel);
                if (!File.Exists(srcPath) || FileChanged(dstPath, srcPath))
                {
                    CopyFile(dstPath, srcPath);
                    changed++;
                }
            }
        }
        Log($"Синхронизация завершена (изменено: {changed}, всего: {total})");
    }

    public void WatchMode()
    {
        Log("Запуск режима отслеживания...");
        watcher = new FileSystemWatcher(source);
        watcher.IncludeSubdirectories = true;
        watcher.NotifyFilter = NotifyFilters.FileName | NotifyFilters.LastWrite | NotifyFilters.Size;
        watcher.Changed += (s, e) => { Thread.Sleep(100); ScanAndSync(); };
        watcher.Created += (s, e) => { Thread.Sleep(100); ScanAndSync(); };
        watcher.Deleted += (s, e) => { Thread.Sleep(100); ScanAndSync(); };
        watcher.EnableRaisingEvents = true;
        while (running) Thread.Sleep(1000);
    }

    public void Interactive()
    {
        Console.WriteLine("📁 SyncFolder Pro — C# Edition");
        Console.WriteLine("Команды: config <source> <target>, sync, watch, status, exit");
        while (true)
        {
            Console.Write("> ");
            string cmd = Console.ReadLine()?.Trim() ?? "";
            if (cmd == "exit") { running = false; watcher?.Dispose(); break; }
            else if (cmd.StartsWith("config"))
            {
                var parts = cmd.Split(' ');
                if (parts.Length >= 3)
                {
                    source = parts[1];
                    target = parts[2];
                    Log($"Источник: {source}, Цель: {target}");
                }
            }
            else if (cmd == "sync") ScanAndSync();
            else if (cmd == "watch") WatchMode();
            else if (cmd == "status")
            {
                Log($"Источник: {source} (exists: {Directory.Exists(source)})");
                Log($"Цель: {target} (exists: {Directory.Exists(target)})");
                Log($"Режим: {mode}");
            }
            else Log("Неизвестная команда");
        }
    }

    public static void Main(string[] args)
    {
        var sync = new SyncFolder(".", "./sync_target");
        if (args.Length >= 2)
        {
            sync = new SyncFolder(args[0], args[1]);
            sync.ScanAndSync();
        }
        else sync.Interactive();
    }
}
