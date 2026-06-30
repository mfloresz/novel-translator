package api

import (
	"io"
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/epubimport"
	"translator-server/internal/store"
)

func registerEpubRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.POST("/epubs/preview", func(e *core.RequestEvent) error {
		if err := e.Request.ParseMultipartForm(64 << 20); err != nil {
			return e.BadRequestError("invalid multipart", err)
		}
		file, header, err := e.Request.FormFile("file")
		if err != nil {
			return e.BadRequestError("file required", err)
		}
		defer file.Close()
		blob, err := io.ReadAll(file)
		if err != nil {
			return e.InternalServerError("failed to read file", err)
		}
		parsed, err := epubimport.Parse(blob, header.Filename)
		if err != nil {
			return e.BadRequestError("parse error", err)
		}
		chapters := make([]map[string]any, len(parsed.Chapters))
		for i, ch := range parsed.Chapters {
			chapters[i] = map[string]any{"title": ch.Title, "content": ch.Content}
		}
		return e.JSON(http.StatusOK, map[string]any{"title": parsed.Title, "author": parsed.Author, "description": parsed.Description, "language": parsed.Language, "series": parsed.Series, "number": parsed.Number, "chapters": chapters})
	})
	api.GET("/epubs", func(e *core.RequestEvent) error {
		novelID := e.Request.URL.Query().Get("novelId")
		items, err := s.Store.ListEpubs(e.Auth.Id, novelID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		out := make([]map[string]any, 0, len(items))
		for _, item := range items {
			out = append(out, epubRecord(item))
		}
		return e.JSON(http.StatusOK, out)
	})
	api.POST("/epubs", func(e *core.RequestEvent) error {
		if err := e.Request.ParseMultipartForm(64 << 20); err != nil {
			return e.BadRequestError("invalid multipart", err)
		}
		novelID := e.Request.FormValue("novelId")
		f, h, err := e.Request.FormFile("file")
		if err != nil {
			return e.BadRequestError("file required", err)
		}
		defer f.Close()
		blob, err := io.ReadAll(f)
		if err != nil {
			return e.InternalServerError("failed to read file", err)
		}
		item, err := s.Store.UpsertEpub(e.Auth.Id, &store.Epub{NovelID: novelID, FileKind: e.Request.FormValue("fileKind"), SourceVariant: e.Request.FormValue("sourceVariant"), Label: e.Request.FormValue("label")}, h.Filename, h.Header.Get("Content-Type"), blob)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusCreated, epubRecord(*item))
	})
	api.GET("/epubs/{id}/download", func(e *core.RequestEvent) error {
		record, fileName, err := s.Store.GetEpubDownloadFile(e.Auth.Id, e.Request.PathValue("id"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		fsys, err := e.App.NewFilesystem()
		if err != nil {
			return e.InternalServerError("filesystem init failure", err)
		}
		defer fsys.Close()
		return fsys.Serve(e.Response, e.Request, record.BaseFilesPath()+"/"+fileName, fileName)
	})
}
