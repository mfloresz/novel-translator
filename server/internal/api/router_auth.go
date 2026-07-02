package api

import (
	"net/http"
	"strings"

	"github.com/pocketbase/pocketbase/apis"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/hook"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

const authCookieName = "auth.token"

func setAuthCookie(e *core.RequestEvent, token string) {
	secure := e.Request.TLS != nil || strings.HasPrefix(e.Request.Header.Get("X-Forwarded-Proto"), "https")
	e.SetCookie(&http.Cookie{
		Name:     authCookieName,
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteStrictMode,
		MaxAge:   30 * 24 * 60 * 60, // 30 days
	})
}

func clearAuthCookie(e *core.RequestEvent) {
	e.SetCookie(&http.Cookie{
		Name:     authCookieName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteStrictMode,
		MaxAge:   -1,
	})
}

// loadAuthFromCookie populates e.Auth from the HttpOnly auth cookie when the
// request has no (or an invalid) Authorization header. PocketBase's built-in
// loadAuthToken middleware only reads the Authorization header, so without
// this the cookie-based token is never picked up and apis.RequireAuth()
// rejects every request once the token is no longer readable by JS.
func loadAuthFromCookie() *hook.Handler[*core.RequestEvent] {
	return &hook.Handler[*core.RequestEvent]{
		Id: "loadAuthFromCookie",
		Func: func(e *core.RequestEvent) error {
			if e.Auth != nil {
				return e.Next()
			}
			cookie, err := e.Request.Cookie(authCookieName)
			if err != nil || cookie.Value == "" {
				return e.Next()
			}
			record, err := e.App.FindAuthRecordByToken(cookie.Value, core.TokenTypeAuth)
			if err == nil && record != nil {
				e.Auth = record
			}
			return e.Next()
		},
	}
}

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
		setAuthCookie(e, result.Token)
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
		setAuthCookie(e, result.Token)
		return e.JSON(http.StatusOK, result)
	})

	protected := auth.Group("")
	protected.Bind(loadAuthFromCookie())
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
		setAuthCookie(e, result.Token)
		return e.JSON(http.StatusOK, result)
	})
	protected.POST("/logout", func(e *core.RequestEvent) error {
		clearAuthCookie(e)
		return e.NoContent(http.StatusNoContent)
	})
}
