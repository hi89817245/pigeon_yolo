package main

import (
	"embed"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

//go:embed project/static/index.html
var indexHTML embed.FS

const defaultPythonPort = "8001"

func main() {
	pythonBaseURL, cleanup, err := ensurePythonService()
	if err != nil {
		log.Fatal(err)
	}
	defer cleanup()

	proxy := newProxy(pythonBaseURL)
	mux := http.NewServeMux()
	mux.HandleFunc("/compare", proxy.ServeHTTP)
	mux.HandleFunc("/search", proxy.ServeHTTP)
	mux.HandleFunc("/embed", proxy.ServeHTTP)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		_, _ = io.WriteString(w, `{"ok":true}`)
	})
	mux.HandleFunc("/image", imageHandler)
	mux.HandleFunc("/", indexHandler)

	addr := ":8000"
	log.Printf("Go 服務已啟動: http://127.0.0.1%s", addr)
	log.Printf("Python 服務: %s", pythonBaseURL)
	if err := http.ListenAndServe(addr, mux); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	data, err := indexHTML.ReadFile("project/static/index.html")
	if err != nil {
		http.Error(w, "index not found", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write(data)
}

func imageHandler(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Query().Get("path")
	if path == "" {
		http.Error(w, "missing path", http.StatusBadRequest)
		return
	}
	if _, err := os.Stat(path); err != nil {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, path)
}

func newProxy(target string) *httputil.ReverseProxy {
	urlValue, err := url.Parse(target)
	if err != nil {
		log.Fatalf("invalid python api url: %v", err)
	}
	proxy := httputil.NewSingleHostReverseProxy(urlValue)
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		http.Error(w, fmt.Sprintf("python service unavailable: %v", err), http.StatusBadGateway)
	}
	return proxy
}

func ensurePythonService() (string, func(), error) {
	if api := strings.TrimSpace(os.Getenv("PYTHON_API_URL")); api != "" {
		return api, func() {}, nil
	}

	port := strings.TrimSpace(os.Getenv("PYTHON_SERVICE_PORT"))
	if port == "" {
		port = defaultPythonPort
	}
	baseURL := "http://127.0.0.1:" + port

	exeDir, err := executableDir()
	if err != nil {
		return "", nil, err
	}

	cmd, err := findPythonCommand(exeDir, port)
	if err != nil {
		return "", nil, err
	}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return "", nil, err
	}

	cleanup := func() {
		_ = cmd.Process.Kill()
		_, _ = cmd.Process.Wait()
	}

	if err := waitForHealth(baseURL+"/health", 20*time.Second); err != nil {
		cleanup()
		return "", nil, err
	}

	return baseURL, cleanup, nil
}

func executableDir() (string, error) {
	path, err := os.Executable()
	if err != nil {
		return "", err
	}
	if runtime.GOOS == "windows" {
		path = strings.ReplaceAll(path, "\\", string(os.PathSeparator))
	}
	return filepath.Dir(path), nil
}

func findPythonCommand(exeDir, port string) (*exec.Cmd, error) {
	serviceDir := filepath.Join(exeDir, "python_service")
	candidates := []string{
		filepath.Join(exeDir, "python_service.exe"),
		filepath.Join(serviceDir, "python_service.exe"),
	}
	for _, candidate := range candidates {
		if fileExists(candidate) {
			cmd := exec.Command(candidate)
			cmd.Dir = exeDir
			cmd.Env = append(os.Environ(), "PYTHON_SERVICE_PORT="+port)
			return cmd, nil
		}
	}

	pythonBin := strings.TrimSpace(os.Getenv("PYTHON_EXECUTABLE"))
	if pythonBin == "" {
		pythonBin = "python"
	}

	script := filepath.Join(serviceDir, "app.py")
	if !fileExists(script) {
		return nil, fmt.Errorf("找不到 Python 服務腳本: %s", script)
	}

	cmd := exec.Command(pythonBin, script)
	cmd.Dir = serviceDir
	cmd.Env = append(os.Environ(), "PYTHON_SERVICE_PORT="+port)
	return cmd, nil
}

func waitForHealth(url string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	client := &http.Client{Timeout: 2 * time.Second}
	for time.Now().Before(deadline) {
		resp, err := client.Get(url)
		if err == nil {
			_ = resp.Body.Close()
			if resp.StatusCode >= 200 && resp.StatusCode < 500 {
				return nil
			}
		}
		time.Sleep(400 * time.Millisecond)
	}
	return fmt.Errorf("等待 Python 服務逾時: %s", url)
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}
