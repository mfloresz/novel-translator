package api

import (
	"fmt"
	"net/http"
	"strconv"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerChapterRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.POST("/db/novels/{novelId}/chapters/clean-preview", func(e *core.RequestEvent) error {
		body := struct {
			ChapterID     string `json:"chapterId"`
			Mode          string `json:"mode"`
			SearchText    string `json:"searchText"`
			ReplaceText   string `json:"replaceText"`
			CaseSensitive bool   `json:"caseSensitive"`
			UseRegex      bool   `json:"useRegex"`
			ApplyTo       string `json:"applyTo"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}

		if !isValidCleanMode(body.Mode) {
			return e.BadRequestError("invalid mode", nil)
		}
		if !isValidApplyTo(body.ApplyTo) {
			return e.BadRequestError("invalid applyTo", nil)
		}
		if body.ChapterID == "" {
			return e.BadRequestError("chapterId is required", nil)
		}

		if _, err := s.Store.GetOwnedNovel(e.Auth.Id, e.Request.PathValue("novelId")); err != nil {
			return notFoundOrForbidden(e, err)
		}

		chapter, err := s.Store.GetChapterAccessible(e.Auth.Id, e.Request.PathValue("novelId"), body.ChapterID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}

		source := cleaningSource(chapter, body.ApplyTo)
		result := ApplyClean(source, CleanOptions{
			Mode:          CleanMode(body.Mode),
			SearchText:    body.SearchText,
			ReplaceText:   body.ReplaceText,
			CaseSensitive: body.CaseSensitive,
			UseRegex:      body.UseRegex,
		})

		return e.JSON(http.StatusOK, CleanPreviewResult{ChapterTitle: chapter.Title, CleanResult: result})
	})
	api.POST("/db/novels/{novelId}/chapters/clean", func(e *core.RequestEvent) error {
		body := struct {
			ChapterIDs    []string `json:"chapterIds"`
			Mode          string   `json:"mode"`
			SearchText    string   `json:"searchText"`
			ReplaceText   string   `json:"replaceText"`
			CaseSensitive bool     `json:"caseSensitive"`
			UseRegex      bool     `json:"useRegex"`
			ApplyTo       string   `json:"applyTo"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}

		if !isValidCleanMode(body.Mode) {
			return e.BadRequestError("invalid mode", nil)
		}
		if !isValidApplyTo(body.ApplyTo) {
			return e.BadRequestError("invalid applyTo", nil)
		}
		if len(body.ChapterIDs) == 0 {
			return e.BadRequestError("chapterIds is required", nil)
		}
		if len(body.ChapterIDs) > maxCleanChapters {
			return e.BadRequestError("too many chapters", fmt.Errorf("max %d", maxCleanChapters))
		}

		if _, err := s.Store.GetOwnedNovel(e.Auth.Id, e.Request.PathValue("novelId")); err != nil {
			return notFoundOrForbidden(e, err)
		}

		opts := CleanOptions{
			Mode:          CleanMode(body.Mode),
			SearchText:    body.SearchText,
			ReplaceText:   body.ReplaceText,
			CaseSensitive: body.CaseSensitive,
			UseRegex:      body.UseRegex,
		}

		modified, skipped, notFound, failed := 0, 0, 0, 0
		for _, chapterID := range body.ChapterIDs {
			chapter, err := s.Store.GetChapterAccessible(e.Auth.Id, e.Request.PathValue("novelId"), chapterID)
			if err != nil {
				notFound++
				continue
			}

			patch := &store.Chapter{
				ID:                chapterID,
				ChapterOrder:      chapter.ChapterOrder,
				Title:             chapter.Title,
				TranslatedTitle:   chapter.TranslatedTitle,
				OriginalContent:   chapter.OriginalContent,
				TranslatedContent: chapter.TranslatedContent,
				RefinedContent:    chapter.RefinedContent,
				Status:            chapter.Status,
				ErrorMessage:      chapter.ErrorMessage,
			}
			changed := false
			hasApplicableContent := false

			if body.ApplyTo == "original" || body.ApplyTo == "all" {
				if chapter.OriginalContent != "" {
					hasApplicableContent = true
					res := ApplyClean(chapter.OriginalContent, opts)
					if res.Changed {
						patch.OriginalContent = res.Cleaned
						changed = true
					}
				}
			}
			if body.ApplyTo == "translated" || body.ApplyTo == "all" {
				if chapter.TranslatedContent != "" {
					hasApplicableContent = true
					res := ApplyClean(chapter.TranslatedContent, opts)
					if res.Changed {
						patch.TranslatedContent = res.Cleaned
						changed = true
					}
				}
			}
			if body.ApplyTo == "refined" || body.ApplyTo == "all" {
				if chapter.RefinedContent != "" {
					hasApplicableContent = true
					res := ApplyClean(chapter.RefinedContent, opts)
					if res.Changed {
						patch.RefinedContent = res.Cleaned
						changed = true
					}
				}
			}

			if !changed {
				if !hasApplicableContent {
					skipped++
				}
				continue
			}

			if _, err := s.Store.UpsertChapterWithoutStats(e.Auth.Id, e.Request.PathValue("novelId"), patch); err != nil {
				failed++
				continue
			}
			modified++
		}

		if modified > 0 {
			if err := s.Store.RecalculateNovelStats(e.Request.PathValue("novelId")); err != nil {
				return e.InternalServerError("failed to recalculate stats", err)
			}
		}

		return e.JSON(http.StatusOK, map[string]any{
			"modified": modified,
			"total":    len(body.ChapterIDs),
			"skipped":  skipped,
			"notFound": notFound,
			"failed":   failed,
		})
	})
	api.GET("/db/novels/{novelId}/chapters", func(e *core.RequestEvent) error {
		chapters, err := s.Store.ListAllChapterSummariesAccessible(e.Auth.Id, e.Request.PathValue("novelId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		out := make([]map[string]any, 0, len(chapters))
		for _, ch := range chapters {
			out = append(out, chapterSummaryRecord(ch))
		}
		return e.JSON(http.StatusOK, out)
	})
	api.GET("/db/novels/{novelId}/chapters/full", func(e *core.RequestEvent) error {
		chapters, err := s.Store.ListChaptersAccessible(e.Auth.Id, e.Request.PathValue("novelId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		out := make([]map[string]any, 0, len(chapters))
		for _, ch := range chapters {
			out = append(out, chapterRecord(ch))
		}
		return e.JSON(http.StatusOK, out)
	})
	api.GET("/db/novels/{novelId}/chapter-summaries", func(e *core.RequestEvent) error {
		limit, _ := strconv.Atoi(e.Request.URL.Query().Get("limit"))
		offset, _ := strconv.Atoi(e.Request.URL.Query().Get("offset"))
		items, total, err := s.Store.ListChapterSummariesAccessible(e.Auth.Id, e.Request.PathValue("novelId"), limit, offset)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		out := make([]map[string]any, 0, len(items))
		for _, ch := range items {
			out = append(out, chapterSummaryRecord(ch))
		}
		return e.JSON(http.StatusOK, map[string]any{"items": out, "total": total, "limit": limit, "offset": offset})
	})
	api.GET("/db/novels/{novelId}/chapter-stats", func(e *core.RequestEvent) error {
		stats, err := s.Store.GetChapterStatsAccessible(e.Auth.Id, e.Request.PathValue("novelId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, chapterStatsRecord(stats))
	})
	api.GET("/db/novels/{novelId}/chapters/{chapterId}", func(e *core.RequestEvent) error {
		chapter, err := s.Store.GetChapterAccessible(e.Auth.Id, e.Request.PathValue("novelId"), e.Request.PathValue("chapterId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, chapterRecord(*chapter))
	})
	api.POST("/db/novels/{novelId}/chapters", func(e *core.RequestEvent) error {
		body := store.Chapter{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		chapter, err := s.Store.UpsertChapter(e.Auth.Id, e.Request.PathValue("novelId"), &body)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusCreated, chapterRecord(*chapter))
	})
	api.DELETE("/db/novels/{novelId}/chapters/{chapterId}", func(e *core.RequestEvent) error {
		if err := s.Store.DeleteChapter(e.Auth.Id, e.Request.PathValue("novelId"), e.Request.PathValue("chapterId")); err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, map[string]any{"ok": true})
	})
	api.POST("/db/novels/{novelId}/chapters/bulk-delete", func(e *core.RequestEvent) error {
		body := struct {
			IDs []string `json:"ids"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		deleted, err := s.Store.BulkDeleteChapters(e.Auth.Id, e.Request.PathValue("novelId"), body.IDs)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, map[string]any{"deleted": deleted, "requested": len(body.IDs)})
	})
	api.PATCH("/db/novels/{novelId}/chapters/{chapterId}/status", func(e *core.RequestEvent) error {
		body := struct {
			Status       string `json:"status"`
			ErrorMessage string `json:"errorMessage"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if err := s.Store.UpdateChapterStatusForUser(e.Auth.Id, e.Request.PathValue("novelId"), e.Request.PathValue("chapterId"), body.Status, body.ErrorMessage); err != nil {
			return notFoundOrForbidden(e, err)
		}
		chapter, err := s.Store.GetChapterAccessible(e.Auth.Id, e.Request.PathValue("novelId"), e.Request.PathValue("chapterId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, chapterRecord(*chapter))
	})
}
