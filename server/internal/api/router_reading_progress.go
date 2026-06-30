package api

import (
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
)

func registerReadingProgressRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.GET("/user/novels/{novelId}/reading-progress", func(e *core.RequestEvent) error {
		novelID := e.Request.PathValue("novelId")
		if novelID == "" {
			return e.BadRequestError("novelId is required", nil)
		}
		if _, err := s.Store.GetNovelAccessible(e.Auth.Id, novelID); err != nil {
			return notFoundOrForbidden(e, err)
		}
		rp, err := s.Store.GetReadingProgress(e.Auth.Id, novelID)
		if err != nil {
			return e.JSON(http.StatusOK, map[string]any{})
		}
		return e.JSON(http.StatusOK, readingProgressRecord(*rp))
	})

	api.PUT("/user/novels/{novelId}/reading-progress", func(e *core.RequestEvent) error {
		novelID := e.Request.PathValue("novelId")
		if novelID == "" {
			return e.BadRequestError("novelId is required", nil)
		}
		if _, err := s.Store.GetOwnedNovel(e.Auth.Id, novelID); err != nil {
			return notFoundOrForbidden(e, err)
		}
		body := struct {
			ChapterID     string  `json:"chapterId"`
			ScrollPercent float64 `json:"scrollPercent"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if body.ChapterID == "" {
			return e.BadRequestError("chapterId is required", nil)
		}
		rp, err := s.Store.UpsertReadingProgress(e.Auth.Id, novelID, body.ChapterID, body.ScrollPercent)
		if err != nil {
			return e.InternalServerError("failed to save reading progress", err)
		}
		return e.JSON(http.StatusOK, readingProgressRecord(*rp))
	})
}
