package noveldownloader

import (
	"context"
	"fmt"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

func (p *NovelbinParser) ParseChapter(ctx context.Context, client HTTPClient, chapterURL string) (*Chapter, error) {
	doc, err := client.FetchDocument(ctx, chapterURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapter: %w", err)
	}

	title := strings.TrimSpace(doc.Find("h2").First().Text())
	if title == "" {
		title = strings.TrimSpace(doc.Find("h1").First().Text())
	}

	contentSel := doc.Find("#chr-content")
	if contentSel.Length() == 0 {
		contentSel = doc.Find("#chapter-content")
	}

	if contentSel.Length() == 0 {
		return nil, fmt.Errorf("no chapter content found")
	}

	contentSel.Find(".unlock-buttons, script, style, noscript").Remove()

	contentSel.Find("*").Each(func(_ int, s *goquery.Selection) {
		if style, exists := s.Attr("style"); exists {
			if strings.Contains(strings.ToLower(style), "display:none") {
				s.Remove()
			}
		}
	})

	watermarkText := detectNovelbinWatermark(doc)
	if watermarkText != "" {
		contentSel.Find("p").Each(func(_ int, s *goquery.Selection) {
			if strings.Contains(s.Text(), watermarkText) {
				s.Remove()
			}
		})
	}

	html, err := contentSel.Html()
	if err != nil {
		return nil, fmt.Errorf("getting chapter HTML: %w", err)
	}

	return &Chapter{
		Title:     title,
		Content:   strings.TrimSpace(html),
		SourceURL: chapterURL,
	}, nil
}

func detectNovelbinWatermark(doc *goquery.Document) string {
	const searchToken = `original11Content.replace("`
	var watermark string
	doc.Find("script").EachWithBreak(func(_ int, s *goquery.Selection) bool {
		text := s.Text()
		startIdx := strings.Index(text, searchToken)
		if startIdx == -1 {
			return true
		}
		startIdx += len(searchToken)
		endIdx := strings.Index(text[startIdx:], "\"")
		if endIdx == -1 {
			return true
		}
		watermark = text[startIdx : startIdx+endIdx]
		return false
	})
	return watermark
}
