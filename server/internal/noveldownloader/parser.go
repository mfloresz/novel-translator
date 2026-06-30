package noveldownloader

import (
	"context"

	"github.com/PuerkitoBio/goquery"
)

type Parser interface {
	Name() string
	CanHandle(url string) bool
	GetNovelInfo(ctx context.Context, client HTTPClient, url string) (*NovelInfo, error)
	GetChapterURLs(ctx context.Context, client HTTPClient, doc *goquery.Document, url string) ([]ChapterURL, error)
	ParseChapter(ctx context.Context, client HTTPClient, url string) (*Chapter, error)
}
