package noveldownloader

import (
	"context"
	"testing"
	"time"
)

func TestRealNovelbin(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelbin.com/b/easy-way-of-cultivation-power-harvesting"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	parser := dl.FindParser(url)
	if parser == nil {
		t.Fatalf("no parser found for %s", url)
	}
	t.Logf("parser: %s", parser.Name())

	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("title=%q", info.Title)
	t.Logf("author=%q", info.Author)
	t.Logf("coverURL=%q", info.CoverURL)
	t.Logf("totalChapters=%d", len(info.Chapters))
	desc := info.Description
	if len(desc) > 300 {
		desc = desc[:300] + "..."
	}
	t.Logf("descriptionLen=%d descPreview=%q", len(info.Description), desc)
	if info.CoverURL == "" {
		t.Errorf("empty coverURL")
	}
	if info.Description == "" {
		t.Errorf("empty description")
	}
	if len(info.Chapters) == 0 {
		t.Fatalf("no chapters found")
	}
	t.Logf("first 3 chapters:")
	for i, ch := range info.Chapters {
		if i >= 3 {
			break
		}
		t.Logf("  - %s -> %s", ch.Title, ch.URL)
	}
	t.Logf("last 3 chapters:")
	for i := len(info.Chapters) - 3; i < len(info.Chapters); i++ {
		t.Logf("  - %s -> %s", info.Chapters[i].Title, info.Chapters[i].URL)
	}
}

func TestRealNovelfire(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelfire.net/book/evils-end-martial-god-chronicle"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	parser := dl.FindParser(url)
	if parser == nil {
		t.Fatalf("no parser found for %s", url)
	}
	t.Logf("parser: %s", parser.Name())

	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("title=%q", info.Title)
	t.Logf("author=%q", info.Author)
	t.Logf("coverURL=%q", info.CoverURL)
	t.Logf("totalChapters=%d", len(info.Chapters))
	desc := info.Description
	if len(desc) > 300 {
		desc = desc[:300] + "..."
	}
	t.Logf("descriptionLen=%d descPreview=%q", len(info.Description), desc)
	if info.CoverURL == "" {
		t.Errorf("empty coverURL")
	}
	if info.Description == "" {
		t.Errorf("empty description")
	}
	if len(info.Chapters) == 0 {
		t.Fatalf("no chapters found")
	}
	t.Logf("first 3 chapters:")
	for i, ch := range info.Chapters {
		if i >= 3 {
			break
		}
		t.Logf("  - %s -> %s", ch.Title, ch.URL)
	}
	t.Logf("last 3 chapters:")
	for i := len(info.Chapters) - 3; i < len(info.Chapters); i++ {
		t.Logf("  - %s -> %s", info.Chapters[i].Title, info.Chapters[i].URL)
	}
}

func TestRealNovelbinUserURL(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelbin.com/b/sss-awakening-i-can-class-change-at-will"
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	dl := NewDownloader()
	parser := dl.FindParser(url)
	if parser == nil {
		t.Fatalf("no parser found for %s", url)
	}
	t.Logf("parser: %s", parser.Name())

	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("title=%q", info.Title)
	t.Logf("author=%q", info.Author)
	t.Logf("coverURL=%q", info.CoverURL)
	t.Logf("totalChapters=%d", len(info.Chapters))
	if len(info.Chapters) == 0 {
		t.Fatal("no chapters")
	}
	t.Logf("first chapter: %s -> %s", info.Chapters[0].Title, info.Chapters[0].URL)
	t.Logf("last chapter: %s -> %s", info.Chapters[len(info.Chapters)-1].Title, info.Chapters[len(info.Chapters)-1].URL)

	chapter, err := dl.DownloadChapter(ctx, info.Chapters[0].URL)
	if err != nil {
		t.Fatalf("DownloadChapter: %v", err)
	}
	t.Logf("downloaded first chapter: title=%q markdownLen=%d", chapter.Title, len(chapter.Markdown))
}

func TestRealNovelfireUserURL(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelfire.net/book/cultivating-clan-i-am-the-guardian-spirit-stone"
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	dl := NewDownloader()
	parser := dl.FindParser(url)
	if parser == nil {
		t.Fatalf("no parser found for %s", url)
	}
	t.Logf("parser: %s", parser.Name())

	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("title=%q", info.Title)
	t.Logf("author=%q", info.Author)
	t.Logf("coverURL=%q", info.CoverURL)
	t.Logf("totalChapters=%d", len(info.Chapters))
	if len(info.Chapters) > 0 {
		t.Logf("first chapter: %s -> %s", info.Chapters[0].Title, info.Chapters[0].URL)
		t.Logf("last chapter: %s -> %s", info.Chapters[len(info.Chapters)-1].Title, info.Chapters[len(info.Chapters)-1].URL)
	}
}

func TestRealNovelbinChapter(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelbin.com/b/easy-way-of-cultivation-power-harvesting"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	if len(info.Chapters) == 0 {
		t.Fatal("no chapters to test")
	}
	first := info.Chapters[0]
	t.Logf("downloading first chapter: %s", first.URL)
	chapter, err := dl.DownloadChapter(ctx, first.URL)
	if err != nil {
		t.Fatalf("DownloadChapter: %v", err)
	}
	t.Logf("title=%q contentLen=%d markdownLen=%d", chapter.Title, len(chapter.Content), len(chapter.Markdown))
	if chapter.Title == "" {
		t.Errorf("empty title")
	}
	if len(chapter.Markdown) < 100 {
		t.Errorf("markdown too short: %d bytes", len(chapter.Markdown))
		t.Logf("content=%q", chapter.Content)
		t.Logf("markdown=%q", chapter.Markdown)
	}
}

func TestRealNovelfireChapter(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelfire.net/book/evils-end-martial-god-chronicle"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	if len(info.Chapters) == 0 {
		t.Fatal("no chapters to test")
	}
	first := info.Chapters[0]
	t.Logf("downloading first chapter: %s", first.URL)
	chapter, err := dl.DownloadChapter(ctx, first.URL)
	if err != nil {
		t.Fatalf("DownloadChapter: %v", err)
	}
	t.Logf("title=%q contentLen=%d markdownLen=%d", chapter.Title, len(chapter.Content), len(chapter.Markdown))
	if chapter.Title == "" {
		t.Errorf("empty title")
	}
	if len(chapter.Markdown) < 100 {
		t.Errorf("markdown too short: %d bytes", len(chapter.Markdown))
		t.Logf("content=%q", chapter.Content)
		t.Logf("markdown=%q", chapter.Markdown)
	}
}

func TestRealNovelbinRange(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://novelbin.com/b/easy-way-of-cultivation-power-harvesting"
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	dl := NewDownloader()
	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("downloading chapters 1-3 of %d", len(info.Chapters))
	chapters, err := dl.DownloadChapters(ctx, info.Chapters, 1, 3)
	if err != nil {
		t.Fatalf("DownloadChapters: %v", err)
	}
	if len(chapters) != 3 {
		t.Fatalf("expected 3 chapters, got %d", len(chapters))
	}
	for i, ch := range chapters {
		t.Logf("chapter %d: title=%q markdownLen=%d", i+1, ch.Title, len(ch.Markdown))
	}
}

func TestRealFenrirRealm(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://fenrirealm.com/series/absolute-regression"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	parser := dl.FindParser(url)
	if parser == nil {
		t.Fatalf("no parser found for %s", url)
	}
	t.Logf("parser: %s", parser.Name())

	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("title=%q", info.Title)
	t.Logf("author=%q", info.Author)
	t.Logf("coverURL=%q", info.CoverURL)
	t.Logf("totalChapters=%d", len(info.Chapters))
	desc := info.Description
	if len(desc) > 300 {
		desc = desc[:300] + "..."
	}
	t.Logf("descriptionLen=%d descPreview=%q", len(info.Description), desc)
	if info.CoverURL == "" {
		t.Errorf("empty coverURL")
	}
	if info.Description == "" {
		t.Errorf("empty description")
	}
	if len(info.Chapters) == 0 {
		t.Fatalf("no chapters found")
	}
	t.Logf("first 3 chapters:")
	for i, ch := range info.Chapters {
		if i >= 3 {
			break
		}
		t.Logf("  - %s -> %s", ch.Title, ch.URL)
	}
	t.Logf("last 3 chapters:")
	for i := len(info.Chapters) - 3; i < len(info.Chapters); i++ {
		t.Logf("  - %s -> %s", info.Chapters[i].Title, info.Chapters[i].URL)
	}
}

func TestRealFenrirRealmChapter(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://fenrirealm.com/series/absolute-regression"
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	dl := NewDownloader()
	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	if len(info.Chapters) == 0 {
		t.Fatal("no chapters to test")
	}
	first := info.Chapters[0]
	t.Logf("downloading first chapter: %s", first.URL)
	chapter, err := dl.DownloadChapter(ctx, first.URL)
	if err != nil {
		t.Fatalf("DownloadChapter: %v", err)
	}
	t.Logf("title=%q contentLen=%d markdownLen=%d", chapter.Title, len(chapter.Content), len(chapter.Markdown))
	if chapter.Title == "" {
		t.Errorf("empty title")
	}
	if len(chapter.Markdown) < 100 {
		t.Errorf("markdown too short: %d bytes", len(chapter.Markdown))
		t.Logf("content=%q", chapter.Content)
		t.Logf("markdown=%q", chapter.Markdown)
	}
}

func TestRealFenrirRealmRange(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	url := "https://fenrirealm.com/series/absolute-regression"
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	dl := NewDownloader()
	info, err := dl.GetNovelInfo(ctx, url)
	if err != nil {
		t.Fatalf("GetNovelInfo: %v", err)
	}
	t.Logf("downloading chapters 1-3 of %d", len(info.Chapters))
	chapters, err := dl.DownloadChapters(ctx, info.Chapters, 1, 3)
	if err != nil {
		t.Fatalf("DownloadChapters: %v", err)
	}
	if len(chapters) != 3 {
		t.Fatalf("expected 3 chapters, got %d", len(chapters))
	}
	for i, ch := range chapters {
		t.Logf("chapter %d: title=%q markdownLen=%d", i+1, ch.Title, len(ch.Markdown))
	}
}

func TestRealDownloaderUnsupported(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping real URL test in short mode")
	}
	ctx := context.Background()
	dl := NewDownloader()
	parser := dl.FindParser("https://example.com/novel/foo")
	if parser != nil {
		t.Errorf("expected nil parser for unsupported URL, got %s", parser.Name())
	}
	_, err := dl.GetNovelInfo(ctx, "https://example.com/novel/foo")
	if err == nil {
		t.Errorf("expected error for unsupported URL")
	}
}
