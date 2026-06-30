package noveldownloader

import (
	"context"
	"fmt"
	"net/url"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func (p *NovelbinParser) GetChapterURLs(ctx context.Context, client HTTPClient, doc *goquery.Document, pageURL string) ([]ChapterURL, error) {
	u, err := url.Parse(pageURL)
	if err != nil {
		return nil, err
	}
	slug := strings.TrimSuffix(strings.TrimPrefix(u.Path, "/"), "/")
	parts := strings.Split(slug, "/")
	if len(parts) > 0 {
		slug = parts[len(parts)-1]
	}

	ajaxURL := fmt.Sprintf("https://novelbin.com/ajax/chapter-archive?novelId=%s", slug)
	ajaxBody, err := client.Fetch(ctx, ajaxURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapter archive: %w", err)
	}

	ajaxDoc, err := goquery.NewDocumentFromReader(strings.NewReader(string(ajaxBody)))
	if err != nil {
		return nil, fmt.Errorf("parsing chapter archive: %w", err)
	}

	var chapters []ChapterURL
	ajaxDoc.Find("ul.list-chapter a").Each(func(_ int, s *goquery.Selection) {
		href, exists := s.Attr("href")
		if !exists {
			return
		}
		title := strings.TrimSpace(s.Find(".chapter-title").Text())
		if title == "" {
			title = strings.TrimSpace(s.Text())
		}
		chapters = append(chapters, ChapterURL{
			URL:   resolveURL(pageURL, href),
			Title: CleanTitle(title),
		})
	})

	if len(chapters) == 0 {
		ajaxDoc.Find("template").Each(func(_ int, t *goquery.Selection) {
			t.Find("li a").Each(func(_ int, s *goquery.Selection) {
				href, exists := s.Attr("href")
				if !exists {
					return
				}
				title := strings.TrimSpace(s.Find(".chapter-title").Text())
				if title == "" {
					title = strings.TrimSpace(s.Text())
				}
				chapters = append(chapters, ChapterURL{
					URL:   resolveURL(pageURL, href),
					Title: CleanTitle(title),
				})
			})
		})
	}

	return chapters, nil
}
