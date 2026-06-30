package epubimport

import (
	"html"
	"path"
	"regexp"
	"strings"

	html2md "github.com/JohannesKaufmann/html-to-markdown/v2"
)

var (
	reMetaCoverName    = regexp.MustCompile(`<meta[^>]*name=["']cover["'][^>]*content=["']([^"']+)["']`)
	reMetaCoverProp    = regexp.MustCompile(`<meta[^>]*property=["']cover["'][^>]*>([^<]+)</meta>`)
	reSeriesCalibre    = regexp.MustCompile(`<meta[^>]*name=["']calibre:series["'][^>]*content=["']([^"']+)["']`)
	reSeriesIndexCal   = regexp.MustCompile(`<meta[^>]*name=["']calibre:series_index["'][^>]*content=["']([^"']+)["']`)
	reCollectionName   = regexp.MustCompile(`<meta[^>]*property=["']belongs-to-collection["'][^>]*>([^<]+)</meta>`)
	reCollectionNumber = regexp.MustCompile(`<meta[^>]*property=["']group-position["'][^>]*>([^<]+)</meta>`)
)

func parseMetadata(opfXML string) map[string][]string {
	metadata := map[string][]string{
		"title":       extractTagValues(opfXML, "dc:title"),
		"creator":     extractTagValues(opfXML, "dc:creator"),
		"description": extractTagValues(opfXML, "dc:description"),
		"language":    extractTagValues(opfXML, "dc:language"),
	}
	if series := extractFirstMatch(reSeriesCalibre, opfXML); series != "" {
		metadata["series"] = []string{series}
	} else if series := extractFirstMatch(reCollectionName, opfXML); series != "" {
		metadata["series"] = []string{series}
	}
	if number := extractFirstMatch(reSeriesIndexCal, opfXML); number != "" {
		metadata["number"] = []string{number}
	} else if number := extractFirstMatch(reCollectionNumber, opfXML); number != "" {
		metadata["number"] = []string{number}
	}
	return metadata
}

func parseCoverID(opfXML string) string {
	return firstNonEmpty(extractFirstMatch(reMetaCoverName, opfXML), extractFirstMatch(reMetaCoverProp, opfXML))
}

func findCover(items []manifestItem, coverID string) *manifestItem {
	for _, item := range items {
		if coverID != "" && item.ID == coverID {
			copy := item
			return &copy
		}
	}
	for _, item := range items {
		props := strings.ToLower(item.Properties)
		if strings.Contains(props, "cover-image") {
			copy := item
			return &copy
		}
	}
	for _, item := range items {
		if !strings.HasPrefix(strings.ToLower(item.MediaType), "image/") {
			continue
		}
		name := strings.ToLower(path.Base(item.Href))
		if strings.Contains(name, "cover") {
			copy := item
			return &copy
		}
	}
	return nil
}

func normalizeDescription(value string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return ""
	}
	if md, err := html2md.ConvertString(value); err == nil {
		if cleaned := normalizeMarkdown(md); cleaned != "" {
			return cleaned
		}
	}
	return normalizeInlineText(value)
}

func normalizeInlineText(value string) string {
	value = reTagStrip.ReplaceAllString(value, " ")
	value = html.UnescapeString(value)
	value = strings.Join(strings.Fields(value), " ")
	return strings.TrimSpace(value)
}

func extractTagValues(opfXML, tag string) []string {
	re := regexp.MustCompile(`(?is)<` + regexp.QuoteMeta(tag) + `[^>]*>(.*?)</` + regexp.QuoteMeta(tag) + `>`)
	matches := re.FindAllStringSubmatch(opfXML, -1)
	out := make([]string, 0, len(matches))
	for _, match := range matches {
		if len(match) < 2 {
			continue
		}
		value := normalizeInlineText(match[1])
		if value != "" {
			out = append(out, value)
		}
	}
	return out
}

func extractFirstMatch(re *regexp.Regexp, value string) string {
	match := re.FindStringSubmatch(value)
	if len(match) < 2 {
		return ""
	}
	return normalizeInlineText(match[1])
}

func extractAttr(attrs, key string) string {
	re := regexp.MustCompile(key + `=["']([^"']+)["']`)
	match := re.FindStringSubmatch(attrs)
	if len(match) < 2 {
		return ""
	}
	return strings.TrimSpace(html.UnescapeString(match[1]))
}
