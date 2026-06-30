package noveldownloader

import (
	"context"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"strings"
	"time"

	md "github.com/JohannesKaufmann/html-to-markdown/v2"
)

const (
	// DefaultMinChapterDelay is the default minimum wait between two
	// consecutive chapter fetches. Used to stay below the rate limits of
	// upstream sites like novelfire.net and novelbin.com.
	DefaultMinChapterDelay = 5 * time.Second
	// DefaultMaxChapterDelay is the default maximum wait between two
	// consecutive chapter fetches. A new random value in
	// [min, max] is picked for each gap so the request pattern is less
	// recognizable by upstream defences.
	DefaultMaxChapterDelay = 10 * time.Second
)

type Downloader struct {
	parsers []Parser
	client  HTTPClient
	// MinChapterDelay is the lower bound (inclusive) of the random
	// sleep applied between two consecutive chapter fetches.
	MinChapterDelay time.Duration
	// MaxChapterDelay is the upper bound (inclusive) of the random
	// sleep applied between two consecutive chapter fetches.
	MaxChapterDelay time.Duration
}

func NewDownloader() *Downloader {
	return &Downloader{
		parsers: []Parser{
			NewNovelfireParser(),
			NewNovelbinParser(),
			NewFenrirRealmParser(),
		},
		client:          NewHTTPClient(),
		MinChapterDelay: DefaultMinChapterDelay,
		MaxChapterDelay: DefaultMaxChapterDelay,
	}
}

// NewDownloaderWithClient returns a Downloader that uses the provided
// HTTPClient. Primarily intended for tests that need to redirect remote
// hosts to local fixtures; the inter-chapter delay is disabled so test
// runs stay fast.
func NewDownloaderWithClient(client HTTPClient) *Downloader {
	return &Downloader{
		parsers: []Parser{
			NewNovelfireParser(),
			NewNovelbinParser(),
			NewFenrirRealmParser(),
		},
		client: client,
	}
}

func (d *Downloader) IsSupportedURL(url string) bool {
	return d.FindParser(url) != nil
}

func (d *Downloader) FindParser(url string) Parser {
	for _, p := range d.parsers {
		if p.CanHandle(url) {
			return p
		}
	}
	return nil
}

func (d *Downloader) GetNovelInfo(ctx context.Context, url string) (*NovelInfo, error) {
	parser := d.FindParser(url)
	if parser == nil {
		return nil, fmt.Errorf("unsupported URL: %s", url)
	}
	return parser.GetNovelInfo(ctx, d.client, url)
}

func (d *Downloader) DownloadChapter(ctx context.Context, chapterURL string) (*Chapter, error) {
	parser := d.FindParser(chapterURL)
	if parser == nil {
		return nil, fmt.Errorf("unsupported URL: %s", chapterURL)
	}
	chapter, err := parser.ParseChapter(ctx, d.client, chapterURL)
	if err != nil {
		return nil, err
	}
	if chapter.Content != "" {
		markdown, err := md.ConvertString(chapter.Content)
		if err != nil {
			return nil, fmt.Errorf("converting to markdown: %w", err)
		}
		chapter.Markdown = stripLeadingTitle(cleanMarkdown(markdown))
	}
	return chapter, nil
}

func (d *Downloader) DownloadChapters(ctx context.Context, chapters []ChapterURL, start, end int) ([]Chapter, error) {
	if start < 1 {
		start = 1
	}
	if end > len(chapters) || end < start {
		end = len(chapters)
	}

	var selected []ChapterURL
	for i, ch := range chapters {
		idx := i + 1
		if idx >= start && idx <= end {
			selected = append(selected, ch)
		}
	}

	if len(selected) == 0 {
		return nil, fmt.Errorf("no chapters in range %d-%d (total: %d)", start, end, len(chapters))
	}

	result := make([]Chapter, 0, len(selected))
	for i, ch := range selected {
		if i > 0 {
			if err := d.SleepBetweenChapters(ctx); err != nil {
				return nil, err
			}
		}
		chapter, err := d.DownloadChapter(ctx, ch.URL)
		if err != nil {
			return nil, fmt.Errorf("downloading chapter %q: %w", ch.Title, err)
		}
		result = append(result, *chapter)
	}
	return result, nil
}

// SleepBetweenChapters waits a random duration within
// [MinChapterDelay, MaxChapterDelay] before fetching the next chapter.
// The wait is bounded by the request context so cancellation propagates.
func (d *Downloader) SleepBetweenChapters(ctx context.Context) error {
	min := d.MinChapterDelay
	max := d.MaxChapterDelay
	if min <= 0 && max <= 0 {
		return nil
	}
	if max < min {
		max = min
	}
	var delay time.Duration
	if max == min {
		delay = max
	} else {
		delay = min + time.Duration(rand.Int63n(int64(max-min)))
	}
	if delay <= 0 {
		return nil
	}
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

// stripLeadingTitle removes a markdown heading from the first line of
// content when it looks like a duplicate of the chapter title.
// Some sites (novelfire, novelbin) inject the chapter title as a heading
// inside the content body, causing a duplicate title in the stored content.
func stripLeadingTitle(content string) string {
	trimmed := strings.TrimLeft(content, "\n\t ")
	if trimmed == "" {
		return ""
	}
	// Re-split from the trimmed content so leading whitespace does not
	// cause us to miss a heading on the first non-empty line.
	lines := strings.SplitN(trimmed, "\n", 2)
	first := strings.TrimSpace(lines[0])
	if strings.HasPrefix(first, "# ") ||
		strings.HasPrefix(first, "## ") ||
		strings.HasPrefix(first, "### ") ||
		strings.HasPrefix(first, "#### ") {
		if len(lines) > 1 {
			return strings.TrimSpace(lines[1])
		}
		return ""
	}
	return content
}

func cleanMarkdown(markdown string) string {
	markdown = strings.ReplaceAll(markdown, "\r\n", "\n")
	markdown = strings.ReplaceAll(markdown, "\r", "\n")
	markdown = strings.TrimSpace(markdown)
	for strings.Contains(markdown, "\n\n\n") {
		markdown = strings.ReplaceAll(markdown, "\n\n\n", "\n\n")
	}
	return markdown
}

// DownloadCover fetches a remote image and returns its bytes together with
// the content type reported by the server. The downloader routes the
// request through its configured HTTPClient so that test transports and
// host rewrites apply consistently.
func (d *Downloader) DownloadCover(ctx context.Context, coverURL string) ([]byte, string, error) {
	if strings.TrimSpace(coverURL) == "" {
		return nil, "", fmt.Errorf("empty cover url")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, coverURL, nil)
	if err != nil {
		return nil, "", fmt.Errorf("creating cover request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "image/*,*/*;q=0.8")

	resp, err := d.client.Do(req)
	if err != nil {
		return nil, "", fmt.Errorf("fetching cover: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, "", fmt.Errorf("HTTP %d fetching cover", resp.StatusCode)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, "", fmt.Errorf("reading cover body: %w", err)
	}
	mimeType := resp.Header.Get("Content-Type")
	if mimeType == "" {
		mimeType = "image/jpeg"
	}
	return body, mimeType, nil
}
