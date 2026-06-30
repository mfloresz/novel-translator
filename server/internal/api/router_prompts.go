package api

import (
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerPromptRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.GET("/user/prompts", func(e *core.RequestEvent) error {
		prompts, err := s.Store.ListPrompts(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to load prompts", err)
		}
		return e.JSON(http.StatusOK, promptsToResponse(prompts))
	})
	api.PUT("/user/prompts/{key}", func(e *core.RequestEvent) error {
		key := e.Request.PathValue("key")
		body := struct {
			Label       string `json:"label"`
			Description string `json:"description"`
			Prompt      struct {
				SystemPrompt string `json:"systemPrompt"`
				UserPrompt   string `json:"userPrompt"`
			} `json:"prompt"`
			Active *bool `json:"active"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		active := 1
		if body.Active != nil && !*body.Active {
			active = 0
		}
		prompt, err := s.Store.UpsertPrompt(e.Auth.Id, store.Prompt{Key: key, Label: body.Label, Description: body.Description, SystemPrompt: body.Prompt.SystemPrompt, UserPrompt: body.Prompt.UserPrompt, Active: active})
		if err != nil {
			return e.InternalServerError("failed to update prompt", err)
		}
		return e.JSON(http.StatusOK, promptToResponse(prompt))
	})
}
