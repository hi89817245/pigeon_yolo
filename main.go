package main

import (
	"bytes"
	"embed"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

//go:embed project/static/index.html
var indexHTML embed.FS

type AppConfig struct {
	GoPort                int    `json:"go_port"`
	PythonPort            int    `json:"python_port"`
	ModelsDir             string `json:"models_dir"`
	PythonExecutable      string `json:"python_executable"`
	PythonScript          string `json:"python_script"`
	PythonServiceExe      string `json:"python_service_exe"`
	UploadDir             string `json:"upload_dir"`
	CropDir               string `json:"crop_dir"`
	MaxUploadMB           int    `json:"max_upload_mb"`
	PythonStartTimeoutSec int    `json:"python_start_timeout_sec"`
}

const (
	defaultGoPort                = 8000
	defaultPythonPort            = 8001
	defaultMaxUploadMB           = 20
	defaultPythonStartTimeoutSec = 180
)

func main() {
	baseDir := resolveBaseDir()
	cfg := loadConfig(baseDir)

	pythonBaseURL, cleanup, err := ensurePythonService(baseDir, cfg)
	if err != nil {
		log.Fatal(err)
	}
	defer cleanup()

	goPort := cfg.GoPort
	if goPort <= 0 {
		goPort = defaultGoPort
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/image", imageHandler)
	mux.HandleFunc("/compare", compareHandler(pythonBaseURL, cfg))
	mux.HandleFunc("/search", searchHandler(pythonBaseURL, cfg))
	mux.HandleFunc("/embed", embedHandler(pythonBaseURL, cfg))
	mux.HandleFunc("/", indexHandler)

	addr := fmt.Sprintf(":%d", goPort)
	log.Printf("Go 服務已啟動: http://127.0.0.1%s", addr)
	log.Printf("Python 服務: %s", pythonBaseURL)
	if err := http.ListenAndServe(addr, mux); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}

func defaultConfig() AppConfig {
	return AppConfig{
		GoPort:                defaultGoPort,
		PythonPort:            defaultPythonPort,
		ModelsDir:             "project/assets",
		PythonExecutable:      "python",
		PythonScript:          "python_service/app.py",
		PythonServiceExe:      "python_service.exe",
		UploadDir:             "uploads",
		CropDir:               "tmp/crops",
		MaxUploadMB:           defaultMaxUploadMB,
		PythonStartTimeoutSec: defaultPythonStartTimeoutSec,
	}
}

func loadConfig(baseDir string) AppConfig {
	cfg := defaultConfig()
	path := filepath.Join(baseDir, "config.json")
	data, err := os.ReadFile(path)
	if err != nil {
		return cfg
	}
	_ = json.Unmarshal(data, &cfg)
	if cfg.GoPort <= 0 {
		cfg.GoPort = defaultGoPort
	}
	if cfg.PythonPort <= 0 {
		cfg.PythonPort = defaultPythonPort
	}
	if cfg.MaxUploadMB <= 0 {
		cfg.MaxUploadMB = defaultMaxUploadMB
	}
	if cfg.PythonStartTimeoutSec <= 0 {
		cfg.PythonStartTimeoutSec = defaultPythonStartTimeoutSec
	}
	cfg.ModelsDir = resolvePath(baseDir, cfg.ModelsDir)
	cfg.UploadDir = resolvePath(baseDir, cfg.UploadDir)
	cfg.CropDir = resolvePath(baseDir, cfg.CropDir)
	return cfg
}

func resolveBaseDir() string {
	if cwd, err := os.Getwd(); err == nil {
		if fileExists(filepath.Join(cwd, "config.json")) {
			return cwd
		}
	}
	if exeDir, err := executableDir(); err == nil {
		if fileExists(filepath.Join(exeDir, "config.json")) {
			return exeDir
		}
		return exeDir
	}
	if cwd, err := os.Getwd(); err == nil {
		return cwd
	}
	return "."
}

func resolvePath(baseDir, p string) string {
	if p == "" {
		return ""
	}
	if filepath.IsAbs(p) {
		return p
	}
	return filepath.Clean(filepath.Join(baseDir, p))
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	_, _ = io.WriteString(w, `{"ok":true}`)
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

func compareHandler(pythonBaseURL string, cfg AppConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			methodNotAllowed(w)
			return
		}
		if err := parseMultipart(r, w, cfg); err != nil {
			writeJSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		status, body, err := forwardMultipart(r, pythonBaseURL+"/compare", []string{"img1", "img2"}, nil)
		if err != nil {
			writeJSONError(w, http.StatusBadGateway, err.Error())
			return
		}
		writeUpstreamJSON(w, status, body, false)
	}
}

func searchHandler(pythonBaseURL string, cfg AppConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			methodNotAllowed(w)
			return
		}
		if err := parseMultipart(r, w, cfg); err != nil {
			writeJSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		k := strings.TrimSpace(r.FormValue("k"))
		if k == "" {
			k = "5"
		}
		status, body, err := forwardMultipart(r, pythonBaseURL+"/search", []string{"image"}, map[string]string{"k": k})
		if err != nil {
			writeJSONError(w, http.StatusBadGateway, err.Error())
			return
		}
		writeUpstreamJSON(w, status, body, true)
	}
}

func embedHandler(pythonBaseURL string, cfg AppConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			methodNotAllowed(w)
			return
		}
		if err := parseMultipart(r, w, cfg); err != nil {
			writeJSONError(w, http.StatusBadRequest, err.Error())
			return
		}
		status, body, err := forwardMultipart(r, pythonBaseURL+"/embed", []string{"image"}, nil)
		if err != nil {
			writeJSONError(w, http.StatusBadGateway, err.Error())
			return
		}
		writeUpstreamJSON(w, status, body, true)
	}
}

func parseMultipart(r *http.Request, w http.ResponseWriter, cfg AppConfig) error {
	maxBytes := int64(cfg.MaxUploadMB) * 1024 * 1024
	r.Body = http.MaxBytesReader(w, r.Body, maxBytes)
	if err := r.ParseMultipartForm(maxBytes); err != nil {
		return err
	}
	return nil
}

func forwardMultipart(r *http.Request, endpoint string, fileFields []string, textFields map[string]string) (int, []byte, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	for key, value := range textFields {
		if err := writer.WriteField(key, value); err != nil {
			return 0, nil, err
		}
	}

	for _, field := range fileFields {
		file, header, err := r.FormFile(field)
		if err != nil {
			return 0, nil, fmt.Errorf("missing file %s", field)
		}
		if err := validateUpload(header); err != nil {
			file.Close()
			return 0, nil, err
		}
		part, err := writer.CreateFormFile(field, header.Filename)
		if err != nil {
			file.Close()
			return 0, nil, err
		}
		if _, err := io.Copy(part, file); err != nil {
			file.Close()
			return 0, nil, err
		}
		file.Close()
	}

	if err := writer.Close(); err != nil {
		return 0, nil, err
	}

	req, err := http.NewRequest(http.MethodPost, endpoint, &buf)
	if err != nil {
		return 0, nil, err
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, nil, err
	}
	return resp.StatusCode, body, nil
}

func validateUpload(header *multipart.FileHeader) error {
	if header == nil {
		return fmt.Errorf("invalid upload")
	}
	if header.Size == 0 {
		return fmt.Errorf("empty upload: %s", header.Filename)
	}
	ext := strings.ToLower(filepath.Ext(header.Filename))
	switch ext {
	case ".jpg", ".jpeg", ".png", ".bmp", ".webp":
		return nil
	default:
		return fmt.Errorf("unsupported file type: %s", header.Filename)
	}
}

func writeUpstreamJSON(w http.ResponseWriter, status int, body []byte, rewritePaths bool) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	if !rewritePaths {
		w.WriteHeader(status)
		_, _ = w.Write(body)
		return
	}

	if status < 200 || status >= 300 {
		w.WriteHeader(status)
		_, _ = w.Write(body)
		return
	}

	updated, err := rewriteJSONPaths(body)
	if err != nil {
		w.WriteHeader(status)
		_, _ = w.Write(body)
		return
	}
	w.WriteHeader(status)
	_, _ = w.Write(updated)
}

func rewriteJSONPaths(body []byte) ([]byte, error) {
	var obj map[string]any
	if err := json.Unmarshal(body, &obj); err != nil {
		return nil, err
	}

	if queryCrop, ok := obj["query_crop"].(string); ok && queryCrop != "" {
		obj["query_crop"] = "/image?path=" + queryCrop
	}

	if results, ok := obj["results"].([]any); ok {
		for i, item := range results {
			entry, ok := item.(map[string]any)
			if !ok {
				continue
			}
			if pathValue, ok := entry["path"].(string); ok && pathValue != "" {
				entry["image"] = "/image?path=" + pathValue
			}
			results[i] = entry
		}
		obj["results"] = results
	}

	return json.Marshal(obj)
}

func writeJSONError(w http.ResponseWriter, status int, message string) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write([]byte(fmt.Sprintf(`{"error":%q}`, message)))
}

func methodNotAllowed(w http.ResponseWriter) {
	writeJSONError(w, http.StatusMethodNotAllowed, "method not allowed")
}

func ensurePythonService(baseDir string, cfg AppConfig) (string, func(), error) {
	if api := strings.TrimSpace(os.Getenv("PYTHON_API_URL")); api != "" {
		return api, func() {}, nil
	}

	port := cfg.PythonPort
	if port <= 0 {
		port = defaultPythonPort
	}
	if envPort := strings.TrimSpace(os.Getenv("PYTHON_SERVICE_PORT")); envPort != "" {
		if _, err := fmt.Sscanf(envPort, "%d", &port); err != nil {
			port = cfg.PythonPort
		}
	}
	if port <= 0 {
		port = defaultPythonPort
	}

	baseURL := fmt.Sprintf("http://127.0.0.1:%d", port)
	cmd, err := findPythonCommand(baseDir, cfg, port)
	if err != nil {
		return "", nil, err
	}

	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		return "", nil, err
	}

	cleanup := func() {
		if cmd.Process != nil {
			_ = cmd.Process.Kill()
			_, _ = cmd.Process.Wait()
		}
	}

	timeout := time.Duration(cfg.PythonStartTimeoutSec) * time.Second
	if timeout <= 0 {
		timeout = defaultPythonStartTimeoutSec * time.Second
	}
	if err := waitForHealth(baseURL+"/health", timeout); err != nil {
		cleanup()
		return "", nil, err
	}

	return baseURL, cleanup, nil
}

func findPythonCommand(baseDir string, cfg AppConfig, port int) (*exec.Cmd, error) {
	serviceExe := resolvePath(baseDir, cfg.PythonServiceExe)
	if fileExists(serviceExe) {
		cmd := exec.Command(serviceExe)
		cmd.Dir = baseDir
		cmd.Env = append(os.Environ(),
			"PYTHON_SERVICE_PORT="+fmt.Sprintf("%d", port),
			"PIGEON_MODELS_DIR="+cfg.ModelsDir,
			"PIGEON_CROP_DIR="+cfg.CropDir,
		)
		return cmd, nil
	}

	pythonBin := strings.TrimSpace(cfg.PythonExecutable)
	if pythonBin == "" {
		pythonBin = "python"
	}
	if envPython := strings.TrimSpace(os.Getenv("PYTHON_EXECUTABLE")); envPython != "" {
		pythonBin = envPython
	}

	script := resolvePath(baseDir, cfg.PythonScript)
	if !fileExists(script) {
		return nil, fmt.Errorf("找不到 Python 服務腳本或執行檔: %s", script)
	}
	if uvPath, err := exec.LookPath("uv"); err == nil {
		cmd := exec.Command(uvPath, "run", "python", script)
		cmd.Dir = baseDir
		cmd.Env = append(os.Environ(),
			"PYTHON_SERVICE_PORT="+fmt.Sprintf("%d", port),
			"PIGEON_MODELS_DIR="+cfg.ModelsDir,
			"PIGEON_CROP_DIR="+cfg.CropDir,
		)
		return cmd, nil
	}

	cmd := exec.Command(pythonBin, script)
	cmd.Dir = baseDir
	cmd.Env = append(os.Environ(),
		"PYTHON_SERVICE_PORT="+fmt.Sprintf("%d", port),
		"PIGEON_MODELS_DIR="+cfg.ModelsDir,
		"PIGEON_CROP_DIR="+cfg.CropDir,
	)
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

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}
