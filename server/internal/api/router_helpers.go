package api

import (
	"encoding/json"
	"net/http"
	"strings"

	"translator-server/internal/store"

	"github.com/pocketbase/pocketbase/core"
)

func jsonString(value any, fallback string) string {
	if value == nil {
		return fallback
	}
	b, err := json.Marshal(value)
	if err != nil || string(b) == "null" {
		return fallback
	}
	return string(b)
}

func defaultString(value, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func notFoundOrForbidden(e *core.RequestEvent, err error) error {
	switch err {
	case store.ErrForbidden:
		return e.ForbiddenError("forbidden", err)
	case store.ErrNotFound:
		return e.NotFoundError("not found", err)
	default:
		return e.InternalServerError("internal error", err)
	}
}

func defaultTheme(theme string) string {
	switch theme {
	case "light", "dark", "system":
		return theme
	default:
		return "system"
	}
}

func cleaningSource(ch *store.Chapter, applyTo string) string {
	switch applyTo {
	case "original":
		return ch.OriginalContent
	case "translated":
		return ch.TranslatedContent
	case "refined":
		return ch.RefinedContent
	case "all":
		if ch.RefinedContent != "" {
			return ch.RefinedContent
		}
		if ch.TranslatedContent != "" {
			return ch.TranslatedContent
		}
		return ch.OriginalContent
	default:
		return ""
	}
}

const maxCleanChapters = 500

func isValidCleanMode(mode string) bool {
	switch CleanMode(mode) {
	case CleanModeRemoveAfter, CleanModeRemoveDuplicates, CleanModeRemoveLine, CleanModeRemoveMultipleBlanks, CleanModeSearchReplace:
		return true
	default:
		return false
	}
}

func isValidApplyTo(applyTo string) bool {
	switch applyTo {
	case "original", "translated", "refined", "all":
		return true
	default:
		return false
	}
}

func bearerToken(r *http.Request) string {
	header := strings.TrimSpace(r.Header.Get("Authorization"))
	if !strings.HasPrefix(strings.ToLower(header), "bearer ") {
		return ""
	}
	return strings.TrimSpace(header[7:])
}
