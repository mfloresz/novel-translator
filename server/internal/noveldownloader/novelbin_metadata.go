package noveldownloader

import (
	"context"
	"fmt"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func (p *NovelbinParser) GetNovelInfo(ctx context.Context, client HTTPClient, pageURL string) (*NovelInfo, error) {
	doc, err := client.FetchDocument(ctx, pageURL)
	if err != nil {
		return nil, fmt.Errorf("fetching novel page: %w", err)
	}

	title := strings.TrimSpace(doc.Find("h3.title").First().Text())

	author := ""
	doc.Find("ul.info-meta li").Each(func(_ int, s *goquery.Selection) {
		h3 := strings.TrimSpace(s.Find("h3").Text())
		if strings.EqualFold(h3, "author:") {
			author = strings.TrimSpace(s.Find("a").Text())
		}
	})

	description := extractNovelbinDescription(doc)
	coverURL := extractNovelbinCover(doc)

	chapters, err := p.GetChapterURLs(ctx, client, doc, pageURL)
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

func extractNovelbinDescription(doc *goquery.Document) string {
	candidates := []string{
		"#novel-description-content",
		"div.novel-description-block div.desc-text",
		"div.desc-text",
		"meta[name='description']",
		"meta[property='og:description']",
	}
	for _, sel := range candidates {
		el := doc.Find(sel).First()
		if el.Length() == 0 {
			continue
		}
		var text string
		if strings.HasPrefix(sel, "meta") {
			if content, exists := el.Attr("content"); exists {
				text = content
			}
		} else {
			text = el.Text()
		}
		text = strings.TrimSpace(text)
		if text != "" {
			return text
		}
	}
	return ""
}

func extractNovelbinCover(doc *goquery.Document) string {
	if el := doc.Find("meta[property='og:image']").First(); el.Length() > 0 {
		if content, exists := el.Attr("content"); exists {
			if url := strings.TrimSpace(content); url != "" {
				return url
			}
		}
	}
	if el := doc.Find("div.book img").First(); el.Length() > 0 {
		for _, attr := range []string{"data-src", "data-original", "src"} {
			if v, exists := el.Attr(attr); exists {
				if url := strings.TrimSpace(v); url != "" && !strings.HasPrefix(url, "data:") {
					return url
				}
			}
		}
	}
	return ""
}
