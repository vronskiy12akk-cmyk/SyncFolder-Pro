// sync_js.js — синхронизация папок в локальной сети на JavaScript (Node.js)

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: '> '
});

class SyncFolder {
    constructor(source, target, mode = 'one-way') {
        this.source = source;
        this.target = target;
        this.mode = mode;
        this.filters = [];
        this.logFile = 'sync.log';
        this.verbose = true;
    }

    log(msg) {
        const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19);
        const full = `${timestamp} - ${msg}`;
        if (this.verbose) console.log(`📁 ${full}`);
        fs.appendFileSync(this.logFile, full + '\n');
    }

    shouldIgnore(filePath) {
        const p = filePath;
        for (const f of this.filters) {
            if (p.includes(f)) return true;
        }
        const ignore = ['.git', '__pycache__', '.DS_Store', 'Thumbs.db'];
        for (const ig of ignore) {
            if (p.includes(ig)) return true;
        }
        return false;
    }

    getFileHash(filePath) {
        try {
            const data = fs.readFileSync(filePath);
            return crypto.createHash('md5').update(data).digest('hex');
        } catch (e) {
            return '';
        }
    }

    fileChanged(src, dst) {
        if (!fs.existsSync(dst)) return true;
        const srcStats = fs.statSync(src);
        const dstStats = fs.statSync(dst);
        if (srcStats.size !== dstStats.size) return true;
        if (srcStats.mtime > dstStats.mtime) return true;
        return this.getFileHash(src) !== this.getFileHash(dst);
    }

    copyFile(src, dst) {
        try {
            fs.mkdirSync(path.dirname(dst), { recursive: true });
            fs.copyFileSync(src, dst);
            this.log(`  + ${path.basename(dst)} (copied)`);
            return true;
        } catch (e) {
            this.log(`  ! Ошибка копирования: ${e.message}`);
            return false;
        }
    }

    deleteFile(filePath) {
        try {
            if (fs.existsSync(filePath)) {
                if (fs.statSync(filePath).isDirectory()) {
                    fs.rmSync(filePath, { recursive: true, force: true });
                } else {
                    fs.unlinkSync(filePath);
                }
                this.log(`  - ${path.basename(filePath)} (deleted)`);
            }
            return true;
        } catch (e) {
            this.log(`  ! Ошибка удаления: ${e.message}`);
            return false;
        }
    }

    getFiles(dir) {
        const files = [];
        if (!fs.existsSync(dir)) return files;
        const walk = (currentPath) => {
            const entries = fs.readdirSync(currentPath);
            for (const entry of entries) {
                const fullPath = path.join(currentPath, entry);
                const stats = fs.statSync(fullPath);
                if (stats.isDirectory()) {
                    walk(fullPath);
                } else {
                    if (!this.shouldIgnore(fullPath)) {
                        files.push(fullPath);
                    }
                }
            }
        };
        walk(dir);
        return files;
    }

    scanAndSync() {
        this.log('Начало синхронизации...');
        if (!fs.existsSync(this.source)) {
            this.log('Ошибка: источник не существует');
            return;
        }
        fs.mkdirSync(this.target, { recursive: true });

        const srcFiles = this.getFiles(this.source);
        const dstFiles = this.getFiles(this.target);

        let changed = 0;
        const total = srcFiles.length;

        if (this.mode === 'one-way') {
            for (const srcPath of srcFiles) {
                const rel = path.relative(this.source, srcPath);
                const dstPath = path.join(this.target, rel);
                if (!fs.existsSync(dstPath) || this.fileChanged(srcPath, dstPath)) {
                    this.copyFile(srcPath, dstPath);
                    changed++;
                }
            }
            for (const dstPath of dstFiles) {
                const rel = path.relative(this.target, dstPath);
                const srcPath = path.join(this.source, rel);
                if (!fs.existsSync(srcPath)) {
                    this.deleteFile(dstPath);
                    changed++;
                }
            }
        } else if (this.mode === 'two-way') {
            for (const srcPath of srcFiles) {
                const rel = path.relative(this.source, srcPath);
                const dstPath = path.join(this.target, rel);
                if (!fs.existsSync(dstPath) || this.fileChanged(srcPath, dstPath)) {
                    this.copyFile(srcPath, dstPath);
                    changed++;
                }
            }
            for (const dstPath of dstFiles) {
                const rel = path.relative(this.target, dstPath);
                const srcPath = path.join(this.source, rel);
                if (!fs.existsSync(srcPath) || this.fileChanged(dstPath, srcPath)) {
                    this.copyFile(dstPath, srcPath);
                    changed++;
                }
            }
        }
        this.log(`Синхронизация завершена (изменено: ${changed}, всего: ${total})`);
    }

    interactive() {
        this.log('📁 SyncFolder Pro — JavaScript Edition');
        console.log('Команды: config <source> <target>, sync, status, exit');
        rl.prompt();

        rl.on('line', (line) => {
            const parts = line.trim().split(' ');
            const cmd = parts[0];
            switch (cmd) {
                case 'exit':
                    console.log('До свидания!');
                    rl.close();
                    return;
                case 'config':
                    if (parts.length >= 3) {
                        this.source = parts[1];
                        this.target = parts[2];
                        this.log(`Источник: ${this.source}, Цель: ${this.target}`);
                    }
                    break;
                case 'sync':
                    this.scanAndSync();
                    break;
                case 'status':
                    this.log(`Источник: ${this.source} (exists: ${fs.existsSync(this.source)})`);
                    this.log(`Цель: ${this.target} (exists: ${fs.existsSync(this.target)})`);
                    this.log(`Режим: ${this.mode}`);
                    break;
                default:
                    this.log('Неизвестная команда');
            }
            rl.prompt();
        }).on('close', () => process.exit(0));
    }
}

const args = process.argv.slice(2);
const sync = new SyncFolder('.', './sync_target');
if (args.length >= 2) {
    sync.source = args[0];
    sync.target = args[1];
    sync.scanAndSync();
} else {
    sync.interactive();
}
