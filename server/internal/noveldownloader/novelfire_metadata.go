package noveldownloader

import (
	"context"
	"fmt"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func (p *NovelfireParser) GetNovelInfo(ctx context.Context, client HTTPClient, pageURL string) (*NovelInfo, error) {
	mainURL := pageURL
	chaptersURL := pageURL
	if strings.HasSuffix(chaptersURL, "/chapters") {
		mainURL = strings.TrimSuffix(chaptersURL, "/chapters")
	} else {
		if strings.HasSuffix(chaptersURL, "/") {
			chaptersURL = chaptersURL + "chapters"
		} else {
			chaptersURL = chaptersURL + "/chapters"
		}
	}

	mainDoc, err := client.FetchDocument(ctx, mainURL)
	if err != nil {
		return nil, fmt.Errorf("fetching novel page: %w", err)
	}

	title := extractNovelfireTitle(mainDoc)
	author := extractNovelfireAuthor(mainDoc)
	description := extractNovelfireDescription(mainDoc)
	coverURL := extractNovelfireCover(mainDoc)

	chaptersDoc, err := client.FetchDocument(ctx, chaptersURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapters page: %w", err)
	}
	chapters, err := p.GetChapterURLs(ctx, client, chaptersDoc, chaptersURL)
	if err != nil {
		return nil, fmt.Errorf("getting chapter URLs: %w", err)
	}

	return &NovelInfo{
		Title:       title,
		Author:      author,
		Description: description,
		CoverURL:    coverURL,
		SourceURL:   pageURL,
		Chapters:    chapters,
	}, nil
}

func extractNovelfireTitle(doc *goquery.Document) string {
	selectors := []string{
		"div.main-head h1",
		".main-head h1",
		"div.novel-info h1",
		"h1",
	}
	for _, sel := range selectors {
		titleEl := doc.Find(sel).First()
		if titleEl.Length() == 0 {
			continue
		}
		title := strings.TrimSpace(titleEl.Text())
		if title != "" {
			return cleanNovelfireTitle(title)
		}
	}
	return ""
}

func extractNovelfireAuthor(doc *goquery.Document) string {
	candidates := []string{
		"span[itemprop='author']",
		"a[itemprop='author']",
		".author a",
		".author",
		"ul.books a[href*='/author/']",
	}
	for _, sel := range candidates {
		el := doc.Find(sel).First()
		if el.Length() == 0 {
			continue
		}
		text := strings.TrimSpace(el.Text())
		if text != "" {
			return text
		}
	}
	if el := doc.Find("meta[name='author']").First(); el.Length() > 0 {
		if content, exists := el.Attr("content"); exists {
			if v := strings.TrimSpace(content); v != "" && !strings.EqualFold(v, "Novel Fire") {
				return v
			}
		}
	}
	return ""
}

func extractNovelfireDescription(doc *goquery.Document) string {
	if m := doc.Find("meta[itemprop='description']").First(); m.Length() > 0 {
		if content, exists := m.Attr("content"); exists {
			if v := strings.TrimSpace(content); v != "" {
				return v
			}
		}
	}
	el := doc.Find(".summary .content").First()
	if el.Length() > 0 {
		text := strings.TrimSpace(el.Text())
		if text != "" {
			return text
		}
	}
	el = doc.Find("div.summary").First()
	if el.Length() > 0 {
		text := strings.TrimSpace(el.Text())
		if text != "" {
			return text
		}
	}
	if m := doc.Find("meta[name='description']").First(); m.Length() > 0 {
		if content, exists := m.Attr("content"); exists {
			if v := strings.TrimSpace(content); v != "" && !strings.HasPrefix(strings.ToLower(v), "read ") {
				return v
			}
		}
	}
	return ""
}

func extractNovelfireCover(doc *goquery.Document) string {
	if el := doc.Find("meta[property='og:image']").First(); el.Length() > 0 {
		if content, exists := el.Attr("content"); exists {
			if v := strings.TrimSpace(content); v != "" {
				return v
			}
		}
	}
	if el := doc.Find("meta[name='twitter:image']").First(); el.Length() > 0 {
		if content, exists := el.Attr("content"); exists {
			if v := strings.TrimSpace(content); v != "" {
				return v
			}
		}
	}
	return ""
}

func cleanNovelfireTitle(title string) string {
	suffixes := []string{
		" Novel Chapters - Novel Fire",
		" - Novel Fire",
		" Novel Fire",
		" - Novelfire",
	}
	for _, suffix := range suffixes {
		if strings.HasSuffix(title, suffix) {
			title = strings.TrimSuffix(title, suffix)
			break
		}
	}
	return strings.TrimSpace(title)
}
