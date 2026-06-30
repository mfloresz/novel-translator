package api

import (
	"io/fs"
	"net/http"
	"path"
	"strings"

	translatorserver "translator-server"
)

func staticHandler() http.Handler {
	sub, err := fs.Sub(translatorserver.FrontendFS, "frontend/dist")
	if err != nil {
		panic(err)
	}
	return &spaHandler{fs: http.FS(sub)}
}

type spaHandler struct {
	fs http.FileSystem
}

func (h *spaHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	p := strings.TrimPrefix(r.URL.Path, "/")
	if p == "" {
		p = "index.html"
	}

	ext := path.Ext(p)
	if ext != "" {
		f, err := h.fs.Open(p)
		if err == nil {
			f.Close()
			if strings.HasSuffix(p, ".js") || strings.HasSuffix(p, ".css") {
				w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
			}
			http.FileServer(h.fs).ServeHTTP(w, r)
			return
		}
	}

	idx, err := h.fs.Open("index.html")
	if err != nil {
		http.Error(w, "Not Found", http.StatusNotFound)
		return
	}
	defer idx.Close()
	stat, _ := idx.Stat()
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	http.ServeContent(w, r, "index.html", stat.ModTime(), idx)
}
