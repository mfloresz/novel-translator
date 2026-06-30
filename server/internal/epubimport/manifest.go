package epubimport

import (
	"html"
	"path"
	"regexp"
	"strings"
)

var (
	reManifestItem = regexp.MustCompile(`<item\s+([^>]+?)/?>`)
	reSpineRef     = regexp.MustCompile(`<itemref[^>]*idref=["']([^"']+)["']`)
)

func parseManifest(opfXML string) []manifestItem {
	matches := reManifestItem.FindAllStringSubmatch(opfXML, -1)
	items := make([]manifestItem, 0, len(matches))
	for _, match := range matches {
		attrs := match[1]
		id := extractAttr(attrs, "id")
		href := extractAttr(attrs, "href")
		if id == "" || href == "" {
			continue
		}
		items = append(items, manifestItem{
			ID:         id,
			Href:       html.UnescapeString(href),
			MediaType:  extractAttr(attrs, "media-type"),
			Properties: extractAttr(attrs, "properties"),
		})
	}
	return items
}

func parseSpine(opfXML string) []string {
	matches := reSpineRef.FindAllStringSubmatch(opfXML, -1)
	out := make([]string, 0, len(matches))
	for _, match := range matches {
		if len(match) < 2 {
			continue
		}
		id := strings.TrimSpace(html.UnescapeString(match[1]))
		if id != "" {
			out = append(out, id)
		}
	}
	return out
}

func isHTMLItem(item manifestItem) bool {
	media := strings.ToLower(item.MediaType)
	return strings.Contains(media, "html") || strings.Contains(media, "xhtml")
}

func shouldSkipManifestItem(item manifestItem) bool {
	name := strings.ToLower(path.Base(item.Href))
	props := strings.ToLower(item.Properties)
	if strings.Contains(props, "nav") {
		return true
	}
	return strings.Contains(name, "toc") || strings.Contains(name, "nav") || strings.Contains(name, "contents") || strings.Contains(name, "cover")
}

func shouldSkipChapter(item manifestItem, markdown, htmlString string) bool {
	trimmed := strings.TrimSpace(markdown)
	if len(trimmed) < 80 {
		return true
	}
	name := strings.ToLower(path.Base(item.Href))
	title := strings.ToLower(extractTitle(htmlString, item.Href, 1))
	if looksLikeChapter(title) {
		return false
	}
	if strings.Contains(name, "title") || strings.Contains(name, "copyright") || strings.Contains(name, "index") {
		return len(trimmed) < 1500
	}
	return false
}

func looksLikeChapter(value string) bool {
	value = strings.ToLower(strings.TrimSpace(value))
	keywords := []string{"chapter", "capítulo", "capitulo", "prologue", "prolog", "prólogo", "prologo", "epilogue", "epilog", "epílogo", "epilogo", "part", "book", "act"}
	for _, keyword := range keywords {
		if strings.Contains(value, keyword) {
			return true
		}
	}
	return false
}
