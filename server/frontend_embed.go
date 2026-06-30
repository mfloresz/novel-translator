package translatorserver

import "embed"

// FrontendFS embeds the compiled frontend served by the Go binary.
//
//go:embed all:frontend/dist
var FrontendFS embed.FS
