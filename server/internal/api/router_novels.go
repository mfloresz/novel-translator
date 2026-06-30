package api

import (
	"io"
	"net/http"
	"strconv"
	"strings"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerNovelRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.GET("/db/novels", func(e *core.RequestEvent) error {
		limit, _ := strconv.Atoi(e.Request.URL.Query().Get("limit"))
		selectParam := e.Request.URL.Query().Get("select")
		list, err := s.Store.ListNovels(e.Auth.Id, limit)
		if err != nil {
			return e.InternalServerError("failed to list novels", err)
		}
		items := make([]map[string]any, 0, len(list))
		if selectParam != "" {
			fields := strings.Split(selectParam, ",")
			for i := range list {
				items = append(items, parseJSONFieldsSubset(&list[i], fields))
			}
		} else {
			for i := range list {
				items = append(items, parseJSONFields(&list[i]))
			}
		}
		return e.JSON(http.StatusOK, map[string]any{"items": items, "nextCursor": ""})
	})
	api.POST("/db/novels", func(e *core.RequestEvent) error {
		var in struct {
			SourceLang         string `json:"sourceLanguage"`
			TargetLang         string `json:"targetLanguage"`
			SourceTitle        string `json:"sourceTitle"`
			SourceAuthor       string `json:"sourceAuthor"`
			SourceDescription  string `json:"sourceDescription"`
			SourceSeries       string `json:"sourceSeries"`
			SourceNumber       string `json:"sourceNumber"`
			TargetTitle        string `json:"targetTitle"`
			TargetAuthor       string `json:"targetAuthor"`
			TargetDescription  string `json:"targetDescription"`
			TargetSeries       string `json:"targetSeries"`
			TargetNumber       string `json:"targetNumber"`
			Glossary           any    `json:"glossary"`
			Prompts            any    `json:"prompts"`
			Notes              string `json:"notes"`
			AIOptions          any    `json:"aiOptions"`
			TranslationOptions any    `json:"translationOptions"`
			CleanupRules       any    `json:"cleanupRules"`
			URL                string `json:"url"`
			CustomCommands     string `json:"customCommands"`
			Tags               any    `json:"tags"`
		}
		if err := e.BindBody(&in); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		sourceTitle := strings.TrimSpace(in.SourceTitle)
		if sourceTitle == "" {
			return e.BadRequestError("sourceTitle is required", nil)
		}
		sourceAuthor := strings.TrimSpace(in.SourceAuthor)
		sourceDescription := strings.TrimSpace(in.SourceDescription)
		promptOverrides := store.ParseNovelPromptOverrides(in.Prompts)
		novel := &store.Novel{
			SourceLanguage:          in.SourceLang,
			TargetLanguage:          in.TargetLang,
			SourceTitle:             sourceTitle,
			SourceAuthor:            sourceAuthor,
			SourceDescription:       sourceDescription,
			SourceSeries:            in.SourceSeries,
			SourceNumber:            in.SourceNumber,
			TargetTitle:             in.TargetTitle,
			TargetAuthor:            in.TargetAuthor,
			TargetDescription:       in.TargetDescription,
			TargetSeries:            in.TargetSeries,
			TargetNumber:            in.TargetNumber,
			Glossary:                jsonString(in.Glossary, "[]"),
			TranslationSystemPrompt: promptOverrides.Translation.SystemPrompt,
			TranslationUserPrompt:   promptOverrides.Translation.UserPrompt,
			RefineSystemPrompt:      promptOverrides.Refine.SystemPrompt,
			RefineUserPrompt:        promptOverrides.Refine.UserPrompt,
			CheckSystemPrompt:       promptOverrides.Check.SystemPrompt,
			CheckUserPrompt:         promptOverrides.Check.UserPrompt,
			Notes:                   in.Notes,
			AIOptions:               jsonString(in.AIOptions, "{}"),
			TranslationOptions:      jsonString(in.TranslationOptions, "{}"),
			CleanupRules:            jsonString(in.CleanupRules, "[]"),
			URL:                     in.URL,
			CustomCommands:          in.CustomCommands,
			Status:                  "ongoing",
			Tags:                    jsonString(in.Tags, "[]"),
		}
		if err := s.Store.CreateNovel(e.Auth.Id, novel); err != nil {
			return e.InternalServerError("failed to create novel", err)
		}
		return e.JSON(http.StatusCreated, parseJSONFields(novel))
	})
	api.GET("/db/novels/tags/suggestions", func(e *core.RequestEvent) error {
		limit, _ := strconv.Atoi(e.Request.URL.Query().Get("limit"))
		query := e.Request.URL.Query().Get("q")
		tags, err := s.Store.ListNovelTagSuggestions(e.Auth.Id, query, limit)
		if err != nil {
			return e.InternalServerError("failed to list tag suggestions", err)
		}
		return e.JSON(http.StatusOK, map[string]any{"items": tags})
	})
	api.GET("/db/novels/series/suggestions", func(e *core.RequestEvent) error {
		limit, _ := strconv.Atoi(e.Request.URL.Query().Get("limit"))
		query := e.Request.URL.Query().Get("q")
		series, err := s.Store.ListNovelSeriesSuggestions(e.Auth.Id, query, limit)
		if err != nil {
			return e.InternalServerError("failed to list series suggestions", err)
		}
		return e.JSON(http.StatusOK, map[string]any{"items": series})
	})
	api.GET("/db/novels/{id}", func(e *core.RequestEvent) error {
		novel, err := s.Store.GetNovelAccessible(e.Auth.Id, e.Request.PathValue("id"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, parseJSONFields(novel))
	})
	api.PATCH("/db/novels/{id}", func(e *core.RequestEvent) error {
		patch := map[string]any{}
		if err := e.BindBody(&patch); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		novel, err := s.Store.UpdateNovel(e.Auth.Id, e.Request.PathValue("id"), patch)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, parseJSONFields(novel))
	})
	api.POST("/db/novels/{id}/cover", func(e *core.RequestEvent) error {
		if err := e.Request.ParseMultipartForm(32 << 20); err != nil {
			return e.BadRequestError("failed to parse form", err)
		}
		file, header, err := e.Request.FormFile("cover")
		if err != nil {
			return e.BadRequestError("cover file required", err)
		}
		defer file.Close()
		blob, err := io.ReadAll(file)
		if err != nil {
			return e.InternalServerError("failed to read file", err)
		}
		mimeType := header.Header.Get("Content-Type")
		if mimeType == "" {
			mimeType = "image/jpeg"
		}
		novel, err := s.Store.UpdateNovelCover(e.Auth.Id, e.Request.PathValue("id"), blob, mimeType)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, parseJSONFields(novel))
	})
	api.DELETE("/db/novels/{id}", func(e *core.RequestEvent) error {
		if err := s.Store.DeleteNovel(e.Auth.Id, e.Request.PathValue("id")); err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, map[string]any{"ok": true})
	})
	api.POST("/db/novels/{id}/copy", func(e *core.RequestEvent) error {
		novel, err := s.Store.CopyNovel(e.Auth.Id, e.Request.PathValue("id"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusCreated, parseJSONFields(novel))
	})
	api.PATCH("/db/novels/{id}/visibility", func(e *core.RequestEvent) error {
		body := struct {
			IsPublic bool `json:"isPublic"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		novel, err := s.Store.SetNovelVisibility(e.Auth.Id, e.Request.PathValue("id"), body.IsPublic)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, parseJSONFields(novel))
	})
}
