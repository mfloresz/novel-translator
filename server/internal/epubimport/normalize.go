package epubimport

import (
	"regexp"
	"strings"
)

var (
	reScriptWithContent = regexp.MustCompile(`(?i)<script[^>]*>[\s\S]*?</script>`)
	reScriptSelfClosing = regexp.MustCompile(`(?i)<script[^>]*/>`)
)

func removeScriptTags(s string) string {
	s = reScriptWithContent.ReplaceAllString(s, "")
	s = reScriptSelfClosing.ReplaceAllString(s, "")
	return s
}

func normalizeMarkdown(value string) string {
	value = strings.ReplaceAll(value, "\r\n", "\n")
	value = strings.ReplaceAll(value, "\r", "\n")
	value = strings.ReplaceAll(value, "\u00a0", " ")
	value = strings.TrimSpace(value)
	for strings.Contains(value, "\n\n\n") {
		value = strings.ReplaceAll(value, "\n\n\n", "\n\n")
	}
	return value
}

func stripLeadingMarkdownHeading(md string) string {
	lines := strings.SplitN(md, "\n", 2)
	first := strings.TrimSpace(lines[0])
	if first != "" && first[0] == '#' {
		if len(lines) > 1 {
			return strings.TrimLeft(lines[1], "\n")
		}
		return ""
	}
	return md
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}
