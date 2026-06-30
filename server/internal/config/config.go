package config

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type Config struct {
	Addr              string
	Port              string
	DataDir           string
	StaticDir         string
	AppEncryptionKey  string
	AppEncryptionPath string
	// DownloadMinDelayMs is the lower bound (ms) of the random wait
	// between two consecutive chapter fetches. <= 0 means use the
	// downloader default.
	DownloadMinDelayMs int
	// DownloadMaxDelayMs is the upper bound (ms) of the random wait
	// between two consecutive chapter fetches. <= 0 means use the
	// downloader default.
	DownloadMaxDelayMs int
	MigrateDB          bool
}

func Load() (*Config, error) {
	cfg := &Config{}
	flag.StringVar(&cfg.Addr, "addr", "", "listen address")
	flag.StringVar(&cfg.Port, "port", "", "listen port")
	flag.StringVar(&cfg.DataDir, "data-dir", "", "data directory")
	flag.StringVar(&cfg.StaticDir, "static-dir", "", "dev static dir")
	flag.BoolVar(&cfg.MigrateDB, "migrate-db", false, "migrate legacy database fields before serving")
	flag.Parse()

	if cfg.Addr == "" {
		cfg.Addr = strings.TrimSpace(os.Getenv("ADDR"))
	}
	if cfg.Port == "" {
		cfg.Port = strings.TrimSpace(os.Getenv("PORT"))
	}
	if cfg.Addr == "" {
		port := strings.TrimSpace(cfg.Port)
		if port == "" {
			port = ":5176"
		} else if strings.HasPrefix(port, ":") {
			// port already has a leading colon
		} else {
			port = ":" + port
		}
		cfg.Addr = port
	}

	if cfg.DataDir == "" {
		cfg.DataDir = strings.TrimSpace(os.Getenv("DATA_DIR"))
	}
	if cfg.DataDir == "" {
		execPath, err := os.Executable()
		if err != nil {
			return nil, fmt.Errorf("resolve executable path: %w", err)
		}
		cfg.DataDir = filepath.Join(filepath.Dir(execPath), "data")
	}
	absDataDir, err := filepath.Abs(cfg.DataDir)
	if err != nil {
		return nil, fmt.Errorf("resolve data dir: %w", err)
	}
	cfg.DataDir = absDataDir
	cfg.AppEncryptionPath = filepath.Join(cfg.DataDir, "app.key")

	if cfg.StaticDir == "" {
		cfg.StaticDir = strings.TrimSpace(os.Getenv("STATIC_DIR"))
	}
	if cfg.StaticDir != "" {
		absStaticDir, err := filepath.Abs(cfg.StaticDir)
		if err != nil {
			return nil, fmt.Errorf("resolve static dir: %w", err)
		}
		cfg.StaticDir = absStaticDir
	}

	cfg.AppEncryptionKey = strings.TrimSpace(os.Getenv("APP_ENCRYPTION_KEY"))
	cfg.DownloadMinDelayMs, _ = strconv.Atoi(strings.TrimSpace(os.Getenv("DOWNLOAD_MIN_DELAY_MS")))
	cfg.DownloadMaxDelayMs, _ = strconv.Atoi(strings.TrimSpace(os.Getenv("DOWNLOAD_MAX_DELAY_MS")))
	return cfg, nil
}
