package api

import (
	"net/http"
	"strings"

	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerAuthRoutes(router *pbrouter.Router[*core.RequestEvent], s *Server) {
	auth := router.Group("/api/auth")
	auth.POST("/register", func(e *core.RequestEvent) error {
		body := struct {
			Email    string `json:"email"`
			Password string `json:"password"`
			Name     string `json:"name"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if strings.TrimSpace(body.Email) == "" || strings.TrimSpace(body.Password) == "" {
			return e.BadRequestError("email and password are required", nil)
		}
		result, err := s.Store.CreateUser(body.Email, body.Password, body.Name)
		if err != nil {
			return e.BadRequestError("failed to create user", err)
		}
		return e.JSON(http.StatusCreated, result)
	})
	auth.POST("/login", func(e *core.RequestEvent) error {
		body := struct {
			Email    string `json:"email"`
			Password string `json:"password"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		result, err := s.Store.AuthenticateUser(body.Email, body.Password)
		if err != nil {
			return e.BadRequestError("invalid credentials", nil)
		}
		return e.JSON(http.StatusOK, result)
	})

	protected := auth.Group("")
	protected.Bind(apis.RequireAuth())
	protected.GET("/me", func(e *core.RequestEvent) error {
		return e.JSON(http.StatusOK, store.AuthResult{User: store.User{ID: e.Auth.Id, Email: e.Auth.Email(), Name: e.Auth.GetString("name"), Theme: defaultTheme(e.Auth.GetString("theme")), CreatedAt: e.Auth.GetString("created"), UpdatedAt: e.Auth.GetString("updated")}})
	})
	protected.POST("/refresh", func(e *core.RequestEvent) error {
		token := bearerToken(e.Request)
		result, err := s.Store.RefreshAuth(token)
		if err != nil {
			return e.UnauthorizedError("invalid token", err)
		}
		return e.JSON(http.StatusOK, result)
	})
	protected.POST("/logout", func(e *core.RequestEvent) error {
		return e.NoContent(http.StatusNoContent)
	})
}
