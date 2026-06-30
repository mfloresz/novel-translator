package api

import (
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerSettingsRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.GET("/defaults", func(e *core.RequestEvent) error {
		defaults := store.DefaultTranslationDefaults
		return e.JSON(http.StatusOK, map[string]any{"translation": defaults})
	})

	api.GET("/user/settings", func(e *core.RequestEvent) error {
		settings, err := s.Store.GetAppSettings(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to load settings", err)
		}
		theme, _ := s.Store.GetTheme(e.Auth.Id)
		return e.JSON(http.StatusOK, map[string]any{"theme": theme, "ai": settings.AI, "translation": settings.Translation})
	})
	api.PUT("/user/settings", func(e *core.RequestEvent) error {
		body := struct {
			Theme       string                    `json:"theme"`
			AI          store.AISettings          `json:"ai"`
			Translation store.TranslationDefaults `json:"translation"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if body.Theme != "" {
			if err := s.Store.SaveTheme(e.Auth.Id, body.Theme); err != nil {
				return e.InternalServerError("failed to save theme", err)
			}
		}
		settings, err := s.Store.SaveAppSettings(e.Auth.Id, store.AppSettings{AI: body.AI, Translation: body.Translation})
		if err != nil {
			return e.InternalServerError("failed to save settings", err)
		}
		theme, _ := s.Store.GetTheme(e.Auth.Id)
		return e.JSON(http.StatusOK, map[string]any{"theme": theme, "ai": settings.AI, "translation": settings.Translation})
	})
}
