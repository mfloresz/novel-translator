package epubimport

import (
	"fmt"
	"path"
	"regexp"
	"sort"
	"strings"

	html2md "github.com/JohannesKaufmann/html-to-markdown/v2"
	nhtml "golang.org/x/net/html"
	"golang.org/x/net/html/atom"
)

var (
	reTagStrip = regexp.MustCompile(`<[^>]+>`)
	reHeading  = regexp.MustCompile(`(?is)<h[1-3][^>]*>(.*?)</h[1-3]>`)
	reTitle    = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)
)

func extractTitle(htmlString, href string, chapterIndex int) string {
	if match := reHeading.FindStringSubmatch(htmlString); len(match) > 1 {
		if heading := normalizeInlineText(match[1]); heading != "" {
			return heading
		}
	}
	if match := reTitle.FindStringSubmatch(htmlString); len(match) > 1 {
		if title := normalizeInlineText(match[1]); title != "" {
			return title
		}
	}
	name := strings.TrimSuffix(path.Base(href), path.Ext(href))
	name = strings.ReplaceAll(name, "_", " ")
	name = strings.ReplaceAll(name, "-", " ")
	name = strings.TrimSpace(name)
	if name == "" {
		return fmt.Sprintf("Capítulo %d", chapterIndex)
	}
	return name
}

func splitChaptersFromNCX(htmlContent string, navPoints []ncxNavPoint) []Chapter {
	if len(navPoints) <= 1 {
		return nil
	}

	positions := findChapterHeadingPositions(htmlContent, navPoints)
	if len(positions) < 2 {
		return nil
	}

	fragments := splitHTMLByNavPointPositions(htmlContent, positions, navPoints)
	if len(fragments) == 0 {
		return nil
	}

	var chapters []Chapter
	for _, np := range navPoints {
		fragment, ok := fragments[np.Label]
		if !ok {
			continue
		}

		markdown, err := html2md.ConvertString(fragment)
		if err != nil {
			continue
		}
		markdown = normalizeMarkdown(markdown)
		if markdown == "" {
			continue
		}

		chapters = append(chapters, Chapter{Title: np.Label, Content: markdown})
	}

	return chapters
}

func splitChaptersFromNCXToFragments(htmlContent string, navPoints []ncxNavPoint) map[string]string {
	if len(navPoints) <= 1 {
		return nil
	}

	positions := findChapterHeadingPositions(htmlContent, navPoints)
	if len(positions) < 2 {
		return nil
	}

	fragments := splitHTMLByNavPointPositions(htmlContent, positions, navPoints)
	return fragments
}

func splitChaptersFromHeadings(htmlContent string) []Chapter {
	type headingPos struct {
		label    string
		position int
	}

	var headings []headingPos

	doc, err := nhtml.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return nil
	}

	var search func(*nhtml.Node, bool)
	search = func(n *nhtml.Node, insideAnchor bool) {
		if n.Type == nhtml.ElementNode {
			tag := n.DataAtom
			isLink := tag == atom.A
			isHeading := tag == atom.B || tag == atom.Strong || tag == atom.H1 ||
				tag == atom.H2 || tag == atom.H3 || tag == atom.H4 ||
				tag == atom.H5 || tag == atom.H6 || tag == atom.Em

			if !insideAnchor && isHeading {
				var textBuilder strings.Builder
				var collectText func(*nhtml.Node)
				collectText = func(node *nhtml.Node) {
					if node.Type == nhtml.TextNode {
						textBuilder.WriteString(node.Data)
					}
					for c := node.FirstChild; c != nil; c = c.NextSibling {
						collectText(c)
					}
				}
				collectText(n)

				text := strings.TrimSpace(textBuilder.String())
				normalized := strings.Join(strings.Fields(text), " ")

				if looksLikeChapter(normalized) {
					var buf strings.Builder
					if err := nhtml.Render(&buf, n); err == nil {
						idx := strings.Index(htmlContent, buf.String())
						if idx >= 0 {
							headings = append(headings, headingPos{label: normalized, position: idx})
						}
					}
				}
			}

			for c := n.FirstChild; c != nil; c = c.NextSibling {
				search(c, insideAnchor || isLink)
			}
		} else {
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				search(c, insideAnchor)
			}
		}
	}

	search(doc, false)

	if len(headings) < 2 {
		return nil
	}

	sort.Slice(headings, func(i, j int) bool {
		return headings[i].position < headings[j].position
	})

	var chapters []Chapter
	for i, h := range headings {
		start := h.position
		var end int
		if i+1 < len(headings) {
			end = headings[i+1].position
		} else {
			end = len(htmlContent)
		}

		fragment := htmlContent[start:end]
		fragment = stripLeadingHTMLHeading(fragment)
		if !strings.HasPrefix(strings.TrimSpace(fragment), "<html") &&
			!strings.HasPrefix(strings.TrimSpace(fragment), "<div") &&
			!strings.HasPrefix(strings.TrimSpace(fragment), "<body") {
			fragment = "<div>" + fragment + "</div>"
		}

		markdown, err := html2md.ConvertString(fragment)
		if err != nil {
			continue
		}
		markdown = normalizeMarkdown(markdown)
		if markdown == "" {
			continue
		}

		chapters = append(chapters, Chapter{Title: h.label, Content: markdown})
	}

	return chapters
}

func findChapterHeadingPositions(htmlContent string, navPoints []ncxNavPoint) map[string]int {
	positions := make(map[string]int)

	normalizedLabels := make(map[string]string)
	for _, np := range navPoints {
		normalized := strings.Join(strings.Fields(np.Label), " ")
		normalizedLabels[normalized] = np.Label
	}

	doc, err := nhtml.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return nil
	}

	var search func(*nhtml.Node, bool)
	search = func(n *nhtml.Node, insideAnchor bool) {
		if n.Type == nhtml.ElementNode {
			tag := n.DataAtom
			isLink := tag == atom.A

			isHeading := tag == atom.B || tag == atom.Strong || tag == atom.H1 ||
				tag == atom.H2 || tag == atom.H3 || tag == atom.H4 ||
				tag == atom.H5 || tag == atom.H6 || tag == atom.Em

			if !insideAnchor && isHeading {
				var textBuilder strings.Builder
				var collectText func(*nhtml.Node)
				collectText = func(node *nhtml.Node) {
					if node.Type == nhtml.TextNode {
						textBuilder.WriteString(node.Data)
					}
					for c := node.FirstChild; c != nil; c = c.NextSibling {
						collectText(c)
					}
				}
				collectText(n)

				text := strings.TrimSpace(textBuilder.String())
				normalized := strings.Join(strings.Fields(text), " ")

				if originalLabel, exists := normalizedLabels[normalized]; exists {
					if _, already := positions[originalLabel]; !already {
						var buf strings.Builder
						if err := nhtml.Render(&buf, n); err == nil {
							idx := strings.Index(htmlContent, buf.String())
							if idx >= 0 {
								positions[originalLabel] = idx
							}
						}
					}
				}
			}

			for c := n.FirstChild; c != nil; c = c.NextSibling {
				search(c, insideAnchor || isLink)
			}
		} else {
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				search(c, insideAnchor)
			}
		}
	}

	search(doc, false)

	if len(positions) < 2 {
		return nil
	}

	return positions
}

func splitHTMLByNavPointPositions(htmlContent string, positions map[string]int, navPoints []ncxNavPoint) map[string]string {
	type posEntry struct {
		label    string
		position int
	}
	entries := make([]posEntry, 0, len(positions))
	for _, np := range navPoints {
		if pos, exists := positions[np.Label]; exists {
			entries = append(entries, posEntry{np.Label, pos})
		}
	}
	if len(entries) == 0 {
		return nil
	}

	for i := 0; i < len(entries); i++ {
		for j := i + 1; j < len(entries); j++ {
			if entries[j].position < entries[i].position {
				entries[i], entries[j] = entries[j], entries[i]
			}
		}
	}

	fragments := make(map[string]string, len(entries))
	for i, entry := range entries {
		start := entry.position
		var end int
		if i+1 < len(entries) {
			end = entries[i+1].position
		} else {
			end = len(htmlContent)
		}

		fragment := htmlContent[start:end]
		fragment = stripLeadingHTMLHeading(fragment)
		if !strings.HasPrefix(strings.TrimSpace(fragment), "<html") &&
			!strings.HasPrefix(strings.TrimSpace(fragment), "<div") &&
			!strings.HasPrefix(strings.TrimSpace(fragment), "<body") {
			fragment = "<div>" + fragment + "</div>"
		}
		fragments[entry.label] = fragment
	}

	return fragments
}

func stripLeadingHTMLHeading(html string) string {
	trimmed := strings.TrimLeft(html, " \t\r\n")
	if !strings.HasPrefix(trimmed, "<") {
		return html
	}

	gt := strings.IndexByte(trimmed, '>')
	if gt < 0 {
		return html
	}

	rawTag := trimmed[1:gt]
	tagName, _, _ := strings.Cut(rawTag, " ")
	if tagName == "" {
		tagName = rawTag
	}
	tagName = strings.ToLower(tagName)

	switch tagName {
	case "h1", "h2", "h3", "h4", "h5", "h6", "b", "strong", "em":
	default:
		return html
	}

	trimmedTag := strings.TrimSpace(rawTag)
	if strings.HasSuffix(trimmedTag, "/") {
		return html[:len(html)-len(trimmed)] + trimmed[gt+1:]
	}

	closeTag := "</" + tagName + ">"
	afterOpen := trimmed[gt+1:]
	ci := strings.Index(strings.ToLower(afterOpen), closeTag)
	if ci < 0 {
		return html
	}

	return html[:len(html)-len(trimmed)] + afterOpen[ci+len(closeTag):]
}
