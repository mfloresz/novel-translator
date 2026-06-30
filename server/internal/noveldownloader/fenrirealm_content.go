package noveldownloader

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"

	"html"
)

// fenrirChapterContent maps the JSON returned by
// GET /api/new/v2/series/{slug}/chapters/{chapterSlug}.
type fenrirChapterContent struct {
	ID      int    `json:"id"`
	Slug    string `json:"slug"`
	Name    string `json:"name"`
	Title   string `json:"title"`
	Content string `json:"content"` // TipTap JSON string
	Type    string `json:"type"`
	Number  int    `json:"number"`
}

// tiptapNode represents a node in TipTap's JSON content format.
type tiptapNode struct {
	Type    string        `json:"type"`
	Text    string        `json:"text,omitempty"`
	Content []*tiptapNode `json:"content,omitempty"`
}

// fenrirExtractChapterSlug extracts the series slug and chapter slug from
// a fenrirealm.com chapter URL.
// Expected: https://fenrirealm.com/series/absolute-regression/1
// Returns: ("absolute-regression", "1", nil)
func fenrirExtractChapterSlug(chapterURL string) (seriesSlug, chapterSlug string, err error) {
	u, parseErr := url.Parse(chapterURL)
	if parseErr != nil {
		return "", "", fmt.Errorf("parsing chapter URL: %w", parseErr)
	}
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	// Expected: ["series", "{slug}", "{chapterSlug}"]
	if len(parts) < 3 || parts[0] != "series" {
		return "", "", fmt.Errorf("unexpected chapter URL path: %s", u.Path)
	}
	return parts[1], parts[2], nil
}

func (p *FenrirRealmParser) ParseChapter(ctx context.Context, client HTTPClient, chapterURL string) (*Chapter, error) {
	slug, chSlug, err := fenrirExtractChapterSlug(chapterURL)
	if err != nil {
		return nil, fmt.Errorf("extracting chapter info: %w", err)
	}

	// Fetch chapter content from the API.
	apiURL := fmt.Sprintf("https://fenrirealm.com/api/new/v2/series/%s/chapters/%s", slug, chSlug)
	body, err := client.Fetch(ctx, apiURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapter content: %w", err)
	}

	var chContent fenrirChapterContent
	if err := json.Unmarshal(body, &chContent); err != nil {
		return nil, fmt.Errorf("parsing chapter content: %w", err)
	}

	// Parse the TipTap JSON content.
	var root tiptapNode
	if err := json.Unmarshal([]byte(chContent.Content), &root); err != nil {
		return nil, fmt.Errorf("parsing TipTap content: %w", err)
	}

	// Convert TipTap to HTML (the Downloader will convert HTML to Markdown).
	chapterHTML := tiptapToHTML(&root)

	chapterTitle := chContent.Name
	if chapterTitle == "" {
		chapterTitle = chContent.Title
	}

	return &Chapter{
		Title:     CleanTitle(chapterTitle),
		Content:   chapterHTML,
		SourceURL: chapterURL,
	}, nil
}

// tiptapToHTML converts a TipTap JSON node tree into HTML.
// TipTap uses a structure like:
//
//	{"type":"systemWindow","content":[
//	  {"type":"paragraph","content":[{"type":"text","text":"Hello"}]},
//	  {"type":"paragraph","content":[]},
//	  {"type":"paragraph","content":[{"type":"text","text":"World"}]}
//	]}
//
// This is converted to:
//
//	<p>Hello</p>
//	<p>&nbsp;</p>
//	<p>World</p>
func tiptapToHTML(node *tiptapNode) string {
	if node == nil {
		return ""
	}

	switch node.Type {
	case "text":
		return html.EscapeString(node.Text)
	case "paragraph":
		if len(node.Content) == 0 {
			// Empty paragraph = blank line in the original content.
			return "<p></p>\n"
		}
		var sb strings.Builder
		sb.WriteString("<p>")
		for _, child := range node.Content {
			sb.WriteString(tiptapToHTML(child))
		}
		sb.WriteString("</p>\n")
		return sb.String()
	case "systemWindow", "doc":
		var sb strings.Builder
		for _, child := range node.Content {
			sb.WriteString(tiptapToHTML(child))
		}
		return sb.String()
	default:
		// Unknown node type: recurse into children.
		var sb strings.Builder
		for _, child := range node.Content {
			sb.WriteString(tiptapToHTML(child))
		}
		return sb.String()
	}
}
