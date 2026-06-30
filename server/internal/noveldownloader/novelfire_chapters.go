package noveldownloader

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func (p *NovelfireParser) GetChapterURLs(ctx context.Context, client HTTPClient, doc *goquery.Document, pageURL string) ([]ChapterURL, error) {
	ajaxURL := p.buildChapterListRequestURL(doc, pageURL)
	if ajaxURL != "" {
		chapters, err := fetchNovelfireChaptersJSON(ctx, client, ajaxURL, pageURL)
		if err == nil && len(chapters) > 0 {
			return chapters, nil
		}
	}

	return p.parseChapterListHTML(doc, ctx, client, pageURL)
}

func (p *NovelfireParser) buildChapterListRequestURL(doc *goquery.Document, baseURL string) string {
	const prefix = "/listChapterDataAjax"
	var fragment string
	doc.Find("script").EachWithBreak(func(_ int, s *goquery.Selection) bool {
		text := s.Text()
		startIdx := strings.Index(text, prefix)
		if startIdx == -1 {
			return true
		}
		endIdx := strings.Index(text[startIdx:], "\"")
		if endIdx == -1 {
			endIdx = strings.Index(text[startIdx:], "'")
		}
		if endIdx == -1 {
			return true
		}
		fragment = text[startIdx : startIdx+endIdx]
		return false
	})
	if fragment == "" {
		return ""
	}

	parsed, err := url.Parse(baseURL)
	if err != nil {
		return ""
	}

	return fmt.Sprintf("https://%s%s&draw=1&columns%%5B0%%5D%%5Bdata%%5D=title&columns%%5B0%%5D%%5Bname%%5D=&columns%%5B0%%5D%%5Bsearchable%%5D=true&columns%%5B0%%5D%%5Borderable%%5D=false&columns%%5B0%%5D%%5Bsearch%%5D%%5Bvalue%%5D=&columns%%5B0%%5D%%5Bsearch%%5D%%5Bregex%%5D=false&columns%%5B1%%5D%%5Bdata%%5D=created_at&columns%%5B1%%5D%%5Bname%%5D=&columns%%5B1%%5D%%5Bsearchable%%5D=true&columns%%5B1%%5D%%5Borderable%%5D=true&columns%%5B1%%5D%%5Bsearch%%5D%%5Bvalue%%5D=&columns%%5B1%%5D%%5Bsearch%%5D%%5Bregex%%5D=false&columns%%5B2%%5D%%5Bdata%%5D=n_sort&columns%%5B2%%5D%%5Bname%%5D=&columns%%5B2%%5D%%5Bsearchable%%5D=false&columns%%5B2%%5D%%5Borderable%%5D=true&columns%%5B2%%5D%%5Bsearch%%5D%%5Bvalue%%5D=&columns%%5B2%%5D%%5Bsearch%%5D%%5Bregex%%5D=false&order%%5B0%%5D%%5Bcolumn%%5D=2&order%%5B0%%5D%%5Bdir%%5D=asc&start=0&length=-1&search%%5Bvalue%%5D=&search%%5Bregex%%5D=false",
		parsed.Hostname(), fragment)
}

func fetchNovelfireChaptersJSON(ctx context.Context, client HTTPClient, ajaxURL, pageURL string) ([]ChapterURL, error) {
	data, err := client.Fetch(ctx, ajaxURL)
	if err != nil {
		return nil, err
	}

	var payload struct {
		Data []struct {
			Title string `json:"title"`
			NSort int    `json:"n_sort"`
		} `json:"data"`
	}
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, fmt.Errorf("parsing chapter JSON: %w", err)
	}

	root := pageURL
	if strings.HasSuffix(root, "/chapters") {
		root = strings.TrimSuffix(root, "/chapters")
	}

	chapters := make([]ChapterURL, 0, len(payload.Data))
	for _, ch := range payload.Data {
		chURL := fmt.Sprintf("%s/chapter-%d", root, ch.NSort)
		chapters = append(chapters, ChapterURL{
			URL:   chURL,
			Title: CleanTitle(ch.Title),
		})
	}
	return chapters, nil
}

var chapterURLNumRe = regexp.MustCompile(`chapter-(\d+)$`)

func chapterSortKey(u string) int {
	if m := chapterURLNumRe.FindStringSubmatch(u); len(m) > 1 {
		if n, err := strconv.Atoi(m[1]); err == nil {
			return n
		}
	}
	return 0
}

func (p *NovelfireParser) parseChapterListHTML(doc *goquery.Document, ctx context.Context, client HTTPClient, pageURL string) ([]ChapterURL, error) {
	seen := map[string]bool{}
	var chapters []ChapterURL
	collect := func(d *goquery.Document) {
		d.Find("ul.chapter-list a").Each(func(_ int, s *goquery.Selection) {
			href, exists := s.Attr("href")
			if !exists {
				return
			}
			fullURL := resolveURL(pageURL, href)
			if seen[fullURL] {
				return
			}
			seen[fullURL] = true
			title := strings.TrimSpace(s.Find(".chapter-title").Text())
			if title == "" {
				title = strings.TrimSpace(s.Text())
			}
			chapters = append(chapters, ChapterURL{
				URL:   fullURL,
				Title: CleanTitle(title),
			})
		})
	}

	collect(doc)

	paginationRe := regexp.MustCompile(`[?&]page=(\d+)`)
	processed := map[string]bool{pageURL: true}
	pages := []string{pageURL}

	for i := 0; i < len(pages); i++ {
		d := doc
		if pages[i] != pageURL {
			fetched, err := client.FetchDocument(ctx, pages[i])
			if err != nil {
				continue
			}
			d = fetched
		}
		collect(d)

		d.Find("ul.pagination a").Each(func(_ int, s *goquery.Selection) {
			href, exists := s.Attr("href")
			if !exists {
				return
			}
			fullURL := resolveURL(pageURL, href)
			if !processed[fullURL] && paginationRe.MatchString(fullURL) {
				processed[fullURL] = true
				pages = append(pages, fullURL)
			}
		})
	}

	sort.Slice(chapters, func(i, j int) bool {
		return chapterSortKey(chapters[i].URL) < chapterSortKey(chapters[j].URL)
	})

	return chapters, nil
}
