package noveldownloader

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"time"
)

const delayChapterHTML = `<!doctype html><html><head></head><body>
<h2>Chapter Title</h2>
<div id="chr-content"><p>Body.</p></div>
</body></html>`

type delayTestTransport struct {
	rewrites map[string]string
	inner    http.RoundTripper
}

func (t *delayTestTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	inner := t.inner
	if inner == nil {
		inner = http.DefaultTransport
	}
	rewritten := false
	if target, ok := t.rewrites[req.URL.Host]; ok {
		req2 := req.Clone(req.Context())
		u, err := url.Parse(target)
		if err != nil {
			return nil, err
		}
		req2.URL.Scheme = u.Scheme
		req2.URL.Host = u.Host
		req.Host = u.Host
		req = req2
		rewritten = true
	}
	resp, err := inner.RoundTrip(req)
	if rewritten && resp != nil {
		resp.Request = req
	}
	return resp, err
}

func TestDownloadChaptersAppliesDelayBetweenFetches(t *testing.T) {
	var hits []time.Time
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1</a></li><li><a href="%s">Chapter 2</a></li><li><a href="%s">Chapter 3</a></li></ul>`, chapterURL, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			hits = append(hits, time.Now())
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(delayChapterHTML))
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &delayTestTransport{rewrites: rewrites}
	client := NewHTTPClientWithTransport(transport)

	dl := NewDownloaderWithClient(client)
	dl.MinChapterDelay = 200 * time.Millisecond
	dl.MaxChapterDelay = 200 * time.Millisecond

	chapters := mustGetChapters(t, dl)
	if _, err := dl.DownloadChapters(context.Background(), chapters, 1, 3); err != nil {
		t.Fatalf("download chapters: %v", err)
	}

	if len(hits) != 3 {
		t.Fatalf("expected 3 chapter fetches, got %d", len(hits))
	}
	gap1 := hits[1].Sub(hits[0])
	gap2 := hits[2].Sub(hits[1])
	if gap1 < 180*time.Millisecond {
		t.Errorf("expected >= 200ms gap between chapters 1 and 2, got %v", gap1)
	}
	if gap2 < 180*time.Millisecond {
		t.Errorf("expected >= 200ms gap between chapters 2 and 3, got %v", gap2)
	}
}

func TestDownloadChaptersRespectsContextCancellation(t *testing.T) {
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1</a></li><li><a href="%s">Chapter 2</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(delayChapterHTML))
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &delayTestTransport{rewrites: rewrites}
	client := NewHTTPClientWithTransport(transport)

	dl := NewDownloaderWithClient(client)
	dl.MinChapterDelay = 5 * time.Second
	dl.MaxChapterDelay = 5 * time.Second

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		time.Sleep(50 * time.Millisecond)
		cancel()
	}()
	start := time.Now()
	_, err := dl.DownloadChapters(ctx, mustGetChapters(t, dl), 1, 2)
	elapsed := time.Since(start)
	if err == nil {
		t.Fatalf("expected cancellation error, got nil")
	}
	if !strings.Contains(err.Error(), "context canceled") && !strings.Contains(err.Error(), "context deadline exceeded") {
		t.Errorf("expected context cancellation error, got %v", err)
	}
	if elapsed > 1*time.Second {
		t.Errorf("expected quick cancellation, took %v", elapsed)
	}
}

func TestDownloadChaptersSkipsDelayWhenZero(t *testing.T) {
	var hits []time.Time
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1</a></li><li><a href="%s">Chapter 2</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			hits = append(hits, time.Now())
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(delayChapterHTML))
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &delayTestTransport{rewrites: rewrites}
	client := NewHTTPClientWithTransport(transport)

	dl := NewDownloaderWithClient(client)

	_, err := dl.DownloadChapters(context.Background(), mustGetChapters(t, dl), 1, 2)
	if err != nil {
		t.Fatalf("download chapters: %v", err)
	}
	if len(hits) != 2 {
		t.Fatalf("expected 2 chapter fetches, got %d", len(hits))
	}
	if gap := hits[1].Sub(hits[0]); gap > 100*time.Millisecond {
		t.Errorf("expected near-zero gap without delay, got %v", gap)
	}
}

func mustGetChapters(t *testing.T, dl *Downloader) []ChapterURL {
	t.Helper()
	info, err := dl.GetNovelInfo(context.Background(), "https://novelbin.com/b/test-novel")
	if err != nil {
		t.Fatalf("get novel info: %v", err)
	}
	return info.Chapters
}

const testNovelbinHTML = `<!doctype html><html><head>
<meta property="og:image" content="https://novelbin.com/cover.jpg">
<meta property="og:description" content="Test description.">
</head><body>
<h3 class="title">Mock Test Novel</h3>
<div class="books">
  <div class="book"><img class="lazy" data-src="https://novelbin.com/cover.jpg" alt="cover"></div>
</div>
<div id="novel-description-content" class="desc-text">Test description.</div>
<ul class="info info-meta">
  <li><h3>Author:</h3><a href="/a/Tester">Tester</a></li>
</ul>
</body></html>`
