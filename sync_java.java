// sync_java.java — синхронизация папок в локальной сети на Java

import java.io.*;
import java.nio.file.*;
import java.nio.file.attribute.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.time.*;
import java.time.format.DateTimeFormatter;

public class SyncFolder {
    private Path source, target;
    private String mode; // "one-way", "two-way"
    private List<String> filters = new ArrayList<>();
    private boolean verbose = true;
    private String logFile = "sync.log";
    private boolean running = true;

    public SyncFolder(String src, String dst, String m) {
        this.source = Paths.get(src);
        this.target = Paths.get(dst);
        this.mode = m;
    }

    private void log(String msg) {
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        String full = timestamp + " - " + msg;
        if (verbose) System.out.println("📁 " + full);
        try (FileWriter fw = new FileWriter(logFile, true);
             BufferedWriter bw = new BufferedWriter(fw)) {
            bw.write(full + "\n");
        } catch (IOException e) {}
    }

    private boolean shouldIgnore(Path path) {
        String p = path.toString();
        for (String f : filters) {
            if (p.contains(f)) return true;
        }
        String[] ignore = {".git", "__pycache__", ".DS_Store", "Thumbs.db"};
        for (String ig : ignore) {
            if (p.contains(ig)) return true;
        }
        return false;
    }

    private String getFileHash(Path path) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] buffer = new byte[4096];
            try (InputStream is = Files.newInputStream(path)) {
                int bytes;
                while ((bytes = is.read(buffer)) != -1) {
                    md.update(buffer, 0, bytes);
                }
            }
            byte[] digest = md.digest();
            StringBuilder sb = new StringBuilder();
            for (byte b : digest) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private boolean fileChanged(Path src, Path dst) {
        try {
            if (!Files.exists(dst)) return true;
            if (Files.size(src) != Files.size(dst)) return true;
            if (Files.getLastModifiedTime(src).compareTo(Files.getLastModifiedTime(dst)) > 0) return true;
            return !getFileHash(src).equals(getFileHash(dst));
        } catch (IOException e) {
            return true;
        }
    }

    private boolean copyFile(Path src, Path dst) {
        try {
            Files.createDirectories(dst.getParent());
            Files.copy(src, dst, StandardCopyOption.REPLACE_EXISTING);
            log("  + " + dst.getFileName() + " (copied)");
            return true;
        } catch (IOException e) {
            log("  ! Ошибка копирования: " + e.getMessage());
            return false;
        }
    }

    private boolean deleteFile(Path path) {
        try {
            if (Files.isDirectory(path)) {
                Files.walk(path).sorted(Comparator.reverseOrder()).map(Path::toFile).forEach(File::delete);
            } else {
                Files.delete(path);
            }
            log("  - " + path.getFileName() + " (deleted)");
            return true;
        } catch (IOException e) {
            log("  ! Ошибка удаления: " + e.getMessage());
            return false;
        }
    }

    public void scanAndSync() {
        log("Начало синхронизации...");
        if (!Files.exists(source)) {
            log("Ошибка: источник не существует");
            return;
        }
        try { Files.createDirectories(target); } catch (IOException e) {}

        Map<String, Path> srcFiles = new HashMap<>();
        Map<String, Path> dstFiles = new HashMap<>();

        try {
            Files.walk(source).filter(Files::isRegularFile).forEach(p -> {
                Path rel = source.relativize(p);
                if (!shouldIgnore(rel)) srcFiles.put(rel.toString(), p);
            });
            if (Files.exists(target)) {
                Files.walk(target).filter(Files::isRegularFile).forEach(p -> {
                    Path rel = target.relativize(p);
                    if (!shouldIgnore(rel)) dstFiles.put(rel.toString(), p);
                });
            }
        } catch (IOException e) {
            log("Ошибка сканирования: " + e.getMessage());
            return;
        }

        int changed = 0, total = srcFiles.size();

        if (mode.equals("one-way")) {
            for (Map.Entry<String, Path> entry : srcFiles.entrySet()) {
                Path dstPath = target.resolve(entry.getKey());
                if (!Files.exists(dstPath) || fileChanged(entry.getValue(), dstPath)) {
                    copyFile(entry.getValue(), dstPath);
                    changed++;
                }
            }
            for (Map.Entry<String, Path> entry : dstFiles.entrySet()) {
                if (!srcFiles.containsKey(entry.getKey())) {
                    deleteFile(entry.getValue());
                    changed++;
                }
            }
        } else if (mode.equals("two-way")) {
            for (Map.Entry<String, Path> entry : srcFiles.entrySet()) {
                Path dstPath = target.resolve(entry.getKey());
                if (!Files.exists(dstPath) || fileChanged(entry.getValue(), dstPath)) {
                    copyFile(entry.getValue(), dstPath);
                    changed++;
                }
            }
            for (Map.Entry<String, Path> entry : dstFiles.entrySet()) {
                Path srcPath = source.resolve(entry.getKey());
                if (!Files.exists(srcPath) || fileChanged(entry.getValue(), srcPath)) {
                    copyFile(entry.getValue(), srcPath);
                    changed++;
                }
            }
        }
        log("Синхронизация завершена (изменено: " + changed + ", всего: " + total + ")");
    }

    public void interactive() {
        System.out.println("📁 SyncFolder Pro — Java Edition");
        System.out.println("Команды: config <source> <target>, sync, status, exit");
        Scanner sc = new Scanner(System.in);
        while (true) {
            System.out.print("> ");
            String cmd = sc.nextLine().trim();
            if (cmd.equals("exit")) break;
            else if (cmd.startsWith("config")) {
                String[] parts = cmd.split(" ");
                if (parts.length >= 3) {
                    source = Paths.get(parts[1]);
                    target = Paths.get(parts[2]);
                    log("Источник: " + source + ", Цель: " + target);
                }
            } else if (cmd.equals("sync")) {
                scanAndSync();
            } else if (cmd.equals("status")) {
                log("Источник: " + source + " (exists: " + Files.exists(source) + ")");
                log("Цель: " + target + " (exists: " + Files.exists(target) + ")");
                log("Режим: " + mode);
            } else {
                log("Неизвестная команда");
            }
        }
        sc.close();
    }

    public static void main(String[] args) {
        SyncFolder sync = new SyncFolder(".", "./sync_target", "one-way");
        if (args.length >= 2) {
            sync = new SyncFolder(args[0], args[1], "one-way");
            sync.scanAndSync();
        } else {
            sync.interactive();
        }
    }
}
