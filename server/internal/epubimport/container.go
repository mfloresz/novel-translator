package epubimport

import (
	"fmt"
	"html"
	"regexp"
	"strings"
)

var reRootfile = regexp.MustCompile(`<rootfile[^>]*full-path=["']([^"']+)["']`)

func parseContainer(xml string) (string, error) {
	match := reRootfile.FindStringSubmatch(xml)
	if len(match) < 2 || strings.TrimSpace(match[1]) == "" {
		return "", fmt.Errorf("invalid container.xml: missing rootfile")
	}
	return html.UnescapeString(strings.TrimSpace(match[1])), nil
}
