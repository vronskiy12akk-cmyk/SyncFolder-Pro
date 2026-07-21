// sync_go.go — синхронизация папок в локальной сети на Go

package main

import (
	"bufio"
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type SyncFolder struct {
	source   string
	target   string
	mode     string
	filters  []string
	verbose  bool
	logFile  string
}

func NewSyncFolder(src, dst, mode string) *SyncFolder {
	return &SyncFolder{
		source:  src,
		target:  dst,
		mode:    mode,
		filters: []string{},
		verbose: true,
		logFile: "sync.log",
	}
}

func (s *SyncFolder) log(msg string) {
	timestamp := time.Now().Format("2006-01-02 15:04:05")
	full := timestamp + " - " + msg
	if s.verbose {
		fmt.Println("📁 " + full)
	}
	f, _ := os.OpenFile(s.logFile, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	defer f.Close()
	f.WriteString(full + "\n")
}

func (s *SyncFolder) shouldIgnore(path string) bool {
	for _, f := range s.filters {
		if strings.Contains(path, f) {
			return true
		}
	}
	ignore := []string{".git", "__pycache__", ".DS_Store", "Thumbs.db"}
	for _, ig := range ignore {
		if strings.Contains(path, ig) {
			return true
		}
	}
	return false
}

func (s *SyncFolder) getFileHash(path string) string {
	file, err := os.Open(path)
	if err != nil {
		return ""
	}
	defer file.Close()
	hash := md5.New()
	if _, err := io.Copy(hash, file); err != nil {
		return ""
	}
	return hex.EncodeToString(hash.Sum(nil))
}

func (s *SyncFolder) fileChanged(src, dst string) bool {
	srcInfo, err := os.Stat(src)
	if err != nil {
		return true
	}
	dstInfo, err := os.Stat(dst)
	if err != nil {
		return true
	}
	if srcInfo.Size() != dstInfo.Size() {
		return true
	}
	if srcInfo.ModTime().After(dstInfo.ModTime()) {
		return true
	}
	return s.getFileHash(src) != s.getFileHash(dst)
}

func (s *SyncFolder) copyFile(src, dst string) bool {
	err := os.MkdirAll(filepath.Dir(dst), 0755)
	if err != nil {
		s.log("  ! Ошибка создания папки: " + err.Error())
		return false
	}
	srcFile, err := os.Open(src)
	if err != nil {
		s.log("  ! Ошибка открытия: " + err.Error())
		return false
	}
	defer srcFile.Close()
	dstFile, err := os.Create(dst)
	if err != nil {
		s.log("  ! Ошибка создания: " + err.Error())
		return false
	}
	defer dstFile.Close()
	_, err = io.Copy(dstFile, srcFile)
	if err != nil {
		s.log("  ! Ошибка копирования: " + err.Error())
		return false
	}
	s.log("  + " + filepath.Base(dst) + " (copied)")
	return true
}

func (s *SyncFolder) deleteFile(path string) bool {
	err := os.RemoveAll(path)
	if err != nil {
		s.log("  ! Ошибка удаления: " + err.Error())
		return false
	}
	s.log("  - " + filepath.Base(path) + " (deleted)")
	return true
}

func (s *SyncFolder) getFiles(dir string) []string {
	var files []string
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if !info.IsDir() {
			if !s.shouldIgnore(path) {
				files = append(files, path)
			}
		}
		return nil
	})
	if err != nil {
		s.log("Ошибка сканирования: " + err.Error())
	}
	return files
}

func (s *SyncFolder) scanAndSync() {
	s.log("Начало синхронизации...")
	if _, err := os.Stat(s.source); os.IsNotExist(err) {
		s.log("Ошибка: источник не существует")
		return
	}
	os.MkdirAll(s.target, 0755)

	srcFiles := s.getFiles(s.source)
	dstFiles := s.getFiles(s.target)

	changed := 0
	total := len(srcFiles)

	if s.mode == "one-way" {
		for _, srcPath := range srcFiles {
			rel, _ := filepath.Rel(s.source, srcPath)
			dstPath := filepath.Join(s.target, rel)
			if _, err := os.Stat(dstPath); os.IsNotExist(err) || s.fileChanged(srcPath, dstPath) {
				s.copyFile(srcPath, dstPath)
				changed++
			}
		}
		for _, dstPath := range dstFiles {
			rel, _ := filepath.Rel(s.target, dstPath)
			srcPath := filepath.Join(s.source, rel)
			if _, err := os.Stat(srcPath); os.IsNotExist(err) {
				s.deleteFile(dstPath)
				changed++
			}
		}
	} else if s.mode == "two-way" {
		for _, srcPath := range srcFiles {
			rel, _ := filepath.Rel(s.source, srcPath)
			dstPath := filepath.Join(s.target, rel)
			if _, err := os.Stat(dstPath); os.IsNotExist(err) || s.fileChanged(srcPath, dstPath) {
				s.copyFile(srcPath, dstPath)
				changed++
			}
		}
		for _, dstPath := range dstFiles {
			rel, _ := filepath.Rel(s.target, dstPath)
			srcPath := filepath.Join(s.source, rel)
			if _, err := os.Stat(srcPath); os.IsNotExist(err) || s.fileChanged(dstPath, srcPath) {
				s.copyFile(dstPath, srcPath)
				changed++
			}
		}
	}
	s.log(fmt.Sprintf("Синхронизация завершена (изменено: %d, всего: %d)", changed, total))
}

func (s *SyncFolder) interactive() {
	s.log("📁 SyncFolder Pro — Go Edition")
	fmt.Println("Команды: config <source> <target>, sync, status, exit")
	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Print("> ")
		if !scanner.Scan() {
			break
		}
		cmd := scanner.Text()
		parts := strings.Fields(cmd)
		if len(parts) == 0 {
			continue
		}
		switch parts[0] {
		case "exit":
			return
		case "config":
			if len(parts) >= 3 {
				s.source = parts[1]
				s.target = parts[2]
				s.log("Источник: " + s.source + ", Цель: " + s.target)
			}
		case "sync":
			s.scanAndSync()
		case "status":
			_, srcExists := os.Stat(s.source)
			_, dstExists := os.Stat(s.target)
			s.log("Источник: " + s.source + " (exists: " + fmt.Sprint(srcExists == nil) + ")")
			s.log("Цель: " + s.target + " (exists: " + fmt.Sprint(dstExists == nil) + ")")
			s.log("Режим: " + s.mode)
		default:
			s.log("Неизвестная команда")
		}
	}
}

func main() {
	sync := NewSyncFolder(".", "./sync_target", "one-way")
	if len(os.Args) >= 3 {
		sync.source = os.Args[1]
		sync.target = os.Args[2]
		sync.scanAndSync()
	} else {
		sync.interactive()
	}
}
