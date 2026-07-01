package api

import (
	"context"
	"io/fs"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	translatorserver "translator-server"
	"translator-server/internal/config"
	"translator-server/internal/noveldownloader"
	"translator-server/internal/store"
)

type Server struct {
	Store             *store.Store
	Cfg               *config.Config
	downloadQueue     chan string
	translateQueue    chan string
	queuedJobs        map[string]struct{}
	queueMu           sync.Mutex
	cancelMu          sync.Mutex
	jobCancels        map[string]context.CancelFunc
	DownloaderFactory func() *noveldownloader.Downloader
	previewCacheMu    sync.RWMutex
	previewCache      map[string]previewCacheEntry
}

func New(st *store.Store, cfg *config.Config) *Server {
	s := &Server{Store: st, Cfg: cfg, queuedJobs: map[string]struct{}{}, jobCancels: map[string]context.CancelFunc{}, previewCache: make(map[string]previewCacheEntry)}
	s.DownloaderFactory = func() *noveldownloader.Downloader {
		dl := noveldownloader.NewDownloader()
		if cfg != nil {
			if cfg.DownloadMinDelayMs > 0 {
				dl.MinChapterDelay = time.Duration(cfg.DownloadMinDelayMs) * time.Millisecond
			}
			if cfg.DownloadMaxDelayMs > 0 {
				dl.MaxChapterDelay = time.Duration(cfg.DownloadMaxDelayMs) * time.Millisecond
			}
		}
		return dl
	}
	s.startJobWorker()
	return s
}

func (s *Server) registerJobCancel(jobID string, cancel context.CancelFunc) {
	s.cancelMu.Lock()
	defer s.cancelMu.Unlock()
	s.jobCancels[jobID] = cancel
}

func (s *Server) unregisterJobCancel(jobID string) {
	s.cancelMu.Lock()
	defer s.cancelMu.Unlock()
	delete(s.jobCancels, jobID)
}

func (s *Server) cancelJob(jobID string) {
	s.cancelMu.Lock()
	cancel := s.jobCancels[jobID]
	s.cancelMu.Unlock()
	if cancel != nil {
		cancel()
	}
}

func Router(s *Server) http.Handler {
	router, err := apis.NewRouter(s.Store.App)
	if err != nil {
		panic(err)
	}
	registerRoutes(router, s)
	mux, err := router.BuildMux()
	if err != nil {
		panic(err)
	}
	return mux
}

func registerRoutes(router *pbrouter.Router[*core.RequestEvent], s *Server) {
	router.GET("/healthz", func(e *core.RequestEvent) error {
		return e.JSON(http.StatusOK, map[string]any{"ok": true})
	})

	registerAuthRoutes(router, s)
	registerProtectedRoutes(router, s)
	registerStaticRoutes(router, s.Cfg.StaticDir)
}

func registerProtectedRoutes(router *pbrouter.Router[*core.RequestEvent], s *Server) {
	api := router.Group("/api")
	api.Bind(apis.RequireAuth())

	registerSettingsRoutes(api, s)
	registerProviderRoutes(api, s)
	registerPromptRoutes(api, s)
	registerImportRoutes(api, s)
	registerNovelRoutes(api, s)
	registerChapterRoutes(api, s)
	registerJobRoutes(api, s)
	registerEpubRoutes(api, s)
	registerEpubExportRoutes(api, s)
	registerReadingProgressRoutes(api, s)
}

func registerStaticRoutes(router *pbrouter.Router[*core.RequestEvent], staticDir string) {
	var fsys fs.FS
	if staticDir != "" {
		fsys = os.DirFS(staticDir)
	} else {
		fsys = apis.MustSubFS(translatorserver.FrontendFS, "frontend/dist")
	}
	router.GET("/{path...}", apis.Static(fsys, true))
	router.GET("/{$}", func(e *core.RequestEvent) error {
		return apis.Static(fsys, true)(e)
	})
}
