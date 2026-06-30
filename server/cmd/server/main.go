package main

import (
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"

	"github.com/pocketbase/pocketbase"
	"translator-server/internal/api"
	"translator-server/internal/config"
	"translator-server/internal/secure"
	"translator-server/internal/store"
)

var Version = "dev"

func main() {
	showVersion := flag.Bool("version", false, "print version and exit")
	cfg, err := config.Load()
	if err != nil {
		slog.Error("failed to load config", "error", err)
		os.Exit(1)
	}
	if *showVersion {
		fmt.Println(Version)
		os.Exit(0)
	}

	encryptor, err := secure.NewEncryptorFromConfig(cfg.AppEncryptionKey, cfg.AppEncryptionPath)
	if err != nil {
		slog.Error("failed to create encryptor", "error", err)
		os.Exit(1)
	}

	app := pocketbase.NewWithConfig(pocketbase.Config{
		DefaultDataDir: cfg.DataDir,
		DefaultDev:     cfg.StaticDir != "",
	})
	if err := app.Bootstrap(); err != nil {
		slog.Error("failed to bootstrap pocketbase", "error", err)
		os.Exit(1)
	}

	st := store.New(app, encryptor)
	if err := st.EnsureSchema(); err != nil {
		slog.Error("failed to ensure schema", "error", err)
		os.Exit(1)
	}
	// if cfg.MigrateDB {
	// 	log.Printf("running database migrations")
	// 	if err := st.RunDatabaseMigrations(); err != nil {
	// 		log.Fatal(err)
	// 	}
	// } else {
	// 	needsMigration, err := st.NeedsDatabaseMigration()
	// 	if err != nil {
	// 		log.Fatal(err)
	// 	}
	// 	if needsMigration {
	// 		log.Fatal("legacy novel schema/data detected; run ./translator-server --migrate-db before starting the server")
	// 	}
	// }

	server := api.New(st, cfg)
	handler := api.Router(server)

	slog.Info("translator-server listening", "addr", cfg.Addr, "dataDir", cfg.DataDir)
	if err := http.ListenAndServe(cfg.Addr, handler); err != nil {
		slog.Error("server error", "error", err)
		os.Exit(1)
	}
}
