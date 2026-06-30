package noveldownloader

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

const paginatedChapterListHTMLPage1 = `<!doctype html><html><body>
<article id="chapter-list-page">
<ul class="chapter-list">
<li><a href="/book/test-novel/chapter-1"><span class="chapter-no">1</span><strong class="chapter-title">Chapter 1</strong></a></li>
<li><a href="/book/test-novel/chapter-2"><span class="chapter-no">2</span><strong class="chapter-title">Chapter 2</strong></a></li>
</ul>
<ul class="pagination">
<li><a href="/book/test-novel/chapters?page=2">2</a></li>
<li><a href="/book/test-novel/chapters?page=3">3</a></li>
</ul>
</article>
</body></html>`

const paginatedChapterListHTMLPage2 = `<!doctype html><html><body>
<article id="chapter-list-page">
<ul class="chapter-list">
<li><a href="/book/test-novel/chapter-3"><span class="chapter-no">3</span><strong class="chapter-title">Chapter 3</strong></a></li>
<li><a href="/book/test-novel/chapter-4"><span class="chapter-no">4</span><strong class="chapter-title">Chapter 4</strong></a></li>
</ul>
<ul class="pagination">
<li><a href="/book/test-novel/chapters?page=2">2</a></li>
<li><a href="/book/test-novel/chapters?page=3">3</a></li>
</ul>
</article>
</body></html>`

const paginatedChapterListHTMLPage3 = `<!doctype html><html><body>
<article id="chapter-list-page">
<ul class="chapter-list">
<li><a href="/book/test-novel/chapter-5"><span class="chapter-no">5</span><strong class="chapter-title">Chapter 5</strong></a></li>
</ul>
</article>
</body></html>`

func TestNovelfirePaginatesChapterList(t *testing.T) {
	var pageHits int
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		switch {
		case strings.HasSuffix(r.URL.Path, "/chapters"):
			pageHits++
			switch r.URL.Query().Get("page") {
			case "2":
				_, _ = fmt.Fprint(w, paginatedChapterListHTMLPage2)
			case "3":
				_, _ = fmt.Fprint(w, paginatedChapterListHTMLPage3)
			default:
				_, _ = fmt.Fprint(w, paginatedChapterListHTMLPage1)
			}
		default:
			_, _ = fmt.Fprint(w, `<html><body><h1 itemprop="name">Test Novel</h1></body></html>`)
		}
	}))
	defer mock.Close()

	client := NewHTTPClient()
	parser := &NovelfireParser{}
	doc, err := client.FetchDocument(context.Background(), mock.URL+"/book/test-novel/chapters")
	if err != nil {
		t.Fatalf("FetchDocument: %v", err)
	}
	chapters, err := parser.parseChapterListHTML(doc, context.Background(), client, mock.URL+"/book/test-novel/chapters")
	if err != nil {
		t.Fatalf("parseChapterListHTML: %v", err)
	}
	if len(chapters) != 5 {
		t.Fatalf("expected 5 chapters across 3 pages, got %d", len(chapters))
	}
	for i, ch := range chapters {
		expectedTitle := fmt.Sprintf("Chapter %d", i+1)
		if ch.Title != expectedTitle {
			t.Errorf("chapter %d: expected title %q, got %q", i+1, expectedTitle, ch.Title)
		}
	}
	if pageHits < 3 {
		t.Errorf("expected at least 3 page hits (page 1, 2, 3), got %d", pageHits)
	}
}
