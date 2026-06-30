package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
	"translator-server/internal/noveldownloader"
)

const testNovelbinHTML = `<!doctype html><html><head>
<meta property="og:image" content="https://novelbin.com/cover.jpg">
<meta property="og:description" content="A short test novel used to exercise the URL import endpoint end-to-end.">
</head><body>
<h3 class="title">Mock Test Novel</h3>
<div class="books">
  <div class="book"><img class="lazy" data-src="https://novelbin.com/cover.jpg" alt="cover"></div>
</div>
<div id="novel-description-content" class="desc-text">A short test novel used to exercise the URL import endpoint end-to-end.</div>
<ul class="info info-meta">
  <li><h3>Author:</h3><a href="/a/Tester">Tester</a></li>
</ul>
</body></html>`

const testNovelbinChapterHTML = `<!doctype html><html><head></head><body>
<h2>Chapter 1: First Steps</h2>
<div id="chr-content"><p>It was a dark and stormy night.</p><p>The end.</p></div>
</body></html>`

type hostRewritingTransport struct {
	rewrites map[string]string
	inner    http.RoundTripper
}

func (t *hostRewritingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
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

func TestImportUrlNovelAttachesCoverAndCreatesNovel(t *testing.T) {
	var chapterHits int
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("\xff\xd8\xff\xe0fake-jpeg-bytes"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li></ul>`, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			chapterHits++
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinChapterHTML)
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinHTML)
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{
		"novelbin.com": mock.URL,
	}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-import-url@example.com", "secret123", "Alice")

	novelURL := "https://novelbin.com/b/test-novel"
	resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/import-from-url", alice.Token, map[string]any{
		"url":            novelURL,
		"sourceLanguage": "en",
		"targetLanguage": "es",
	})
	if resp.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", resp.Code, resp.Body.String())
	}

	var importResp struct {
		Novel struct {
			ID                string `json:"id"`
			SourceTitle       string `json:"sourceTitle"`
			SourceAuthor      string `json:"sourceAuthor"`
			SourceDescription string `json:"sourceDescription"`
			URL               string `json:"url"`
			CoverPath         string `json:"coverPath"`
		} `json:"novel"`
		ChaptersImported int `json:"chaptersImported"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &importResp); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if importResp.Novel.ID == "" {
		t.Fatal("expected non-empty novel id")
	}
	if importResp.Novel.SourceTitle != "Mock Test Novel" {
		t.Errorf("unexpected title: %q", importResp.Novel.SourceTitle)
	}
	if importResp.Novel.SourceAuthor != "Tester" {
		t.Errorf("unexpected author: %q", importResp.Novel.SourceAuthor)
	}
	if importResp.Novel.SourceDescription == "" {
		t.Errorf("expected non-empty description")
	}
	if importResp.Novel.URL != novelURL {
		t.Errorf("expected url %q, got %q", novelURL, importResp.Novel.URL)
	}
	if importResp.Novel.CoverPath == "" {
		t.Fatalf("expected coverPath, got empty: %s", resp.Body.String())
	}
	if importResp.ChaptersImported != 1 {
		t.Errorf("expected 1 chapter imported, got %d", importResp.ChaptersImported)
	}
	if chapterHits != 1 {
		t.Errorf("expected chapter endpoint hit 1 time, got %d", chapterHits)
	}

	listResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels", alice.Token, nil)
	if listResp.Code != http.StatusOK {
		t.Fatalf("list failed: %d: %s", listResp.Code, listResp.Body.String())
	}
	var list struct {
		Items []map[string]any `json:"items"`
	}
	if err := json.Unmarshal(listResp.Body.Bytes(), &list); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	found := false
	for _, n := range list.Items {
		if id, _ := n["id"].(string); id == importResp.Novel.ID {
			found = true
			if cp, _ := n["coverPath"].(string); cp == "" {
				t.Errorf("novel in list has empty coverPath")
			}
			break
		}
	}
	if !found {
		t.Errorf("imported novel not present in list")
	}

	coverReq := httptest.NewRequest(http.MethodGet, importResp.Novel.CoverPath, nil)
	coverRec := httptest.NewRecorder()
	env.handler.ServeHTTP(coverRec, coverReq)
	if coverRec.Code != http.StatusOK {
		t.Fatalf("cover fetch returned %d: %s", coverRec.Code, coverRec.Body.String())
	}
	if coverRec.Body.Len() == 0 {
		t.Errorf("expected non-empty cover body")
	}
}

func originFromRequest(r *http.Request) string {
	if r.TLS != nil {
		return "https://" + r.Host
	}
	return "http://" + r.Host
}

func TestPreviewUrlNovelReturnsMetadata(t *testing.T) {
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li><li><a href="%s">Chapter 2: The Journey</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinChapterHTML)
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinHTML)
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{
		"novelbin.com": mock.URL,
	}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-preview-url@example.com", "secret123", "Alice")

	novelURL := "https://novelbin.com/b/test-novel"
	resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/preview-from-url", alice.Token, map[string]any{
		"url": novelURL,
	})
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", resp.Code, resp.Body.String())
	}

	var preview struct {
		Title         string `json:"title"`
		Author        string `json:"author"`
		Description   string `json:"description"`
		CoverURL      string `json:"coverURL"`
		TotalChapters int    `json:"totalChapters"`
		SourceURL     string `json:"sourceURL"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &preview); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if preview.Title != "Mock Test Novel" {
		t.Errorf("title: %q", preview.Title)
	}
	if preview.Author != "Tester" {
		t.Errorf("author: %q", preview.Author)
	}
	if preview.Description == "" {
		t.Errorf("description empty")
	}
	if preview.CoverURL == "" {
		t.Errorf("coverURL empty")
	}
	if preview.TotalChapters != 2 {
		t.Errorf("totalChapters: got %d, want 2", preview.TotalChapters)
	}
	if preview.SourceURL != novelURL {
		t.Errorf("sourceURL: got %q, want %q", preview.SourceURL, novelURL)
	}
}

func TestPreviewUrlNovelRejectsUnsupportedHost(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-preview-bad@example.com", "secret123", "Alice")

	resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/preview-from-url", alice.Token, map[string]any{
		"url": "https://example.com/novel/foo",
	})
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", resp.Code, resp.Body.String())
	}
}

func TestPreviewUrlNovelRejectsEmptyURL(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-preview-empty@example.com", "secret123", "Alice")

	resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/preview-from-url", alice.Token, map[string]any{
		"url": "",
	})
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", resp.Code, resp.Body.String())
	}
}

func TestUpdateUrlPreviewReturnsComparison(t *testing.T) {
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li><li><a href="%s">Chapter 2: The Journey</a></li><li><a href="%s">Chapter 3: The End</a></li></ul>`, chapterURL, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinChapterHTML))
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-update-preview@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")
	patchResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID, alice.Token, map[string]any{
		"url": "https://novelbin.com/b/test-novel",
	})
	assertStatus(t, patchResp, http.StatusOK)

	createChapter(t, env.handler, alice.Token, novel.ID, 1)

	resp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/update-preview", alice.Token, nil)
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", resp.Code, resp.Body.String())
	}

	var preview struct {
		Title           string `json:"title"`
		Author          string `json:"author"`
		CoverURL        string `json:"coverURL"`
		SourceURL       string `json:"sourceURL"`
		CurrentChapters int    `json:"currentChapters"`
		TotalChapters   int    `json:"totalChapters"`
		NewChapters     int    `json:"newChapters"`
		FirstNewChapter int    `json:"firstNewChapter"`
		LastNewChapter  int    `json:"lastNewChapter"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &preview); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if preview.Title != "Mock Test Novel" {
		t.Errorf("title: got %q, want %q", preview.Title, "Mock Test Novel")
	}
	if preview.CoverURL == "" {
		t.Errorf("coverURL should be set")
	}
	if preview.CurrentChapters != 1 {
		t.Errorf("currentChapters: got %d, want 1", preview.CurrentChapters)
	}
	if preview.TotalChapters != 3 {
		t.Errorf("totalChapters: got %d, want 3", preview.TotalChapters)
	}
	if preview.NewChapters != 2 {
		t.Errorf("newChapters: got %d, want 2", preview.NewChapters)
	}
	if preview.FirstNewChapter != 2 {
		t.Errorf("firstNewChapter: got %d, want 2", preview.FirstNewChapter)
	}
	if preview.LastNewChapter != 3 {
		t.Errorf("lastNewChapter: got %d, want 3", preview.LastNewChapter)
	}
}

func TestUpdateUrlPreviewReportsNoneWhenUpToDate(t *testing.T) {
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li><li><a href="%s">Chapter 2: The Journey</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinChapterHTML))
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-update-ok@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")
	patchResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID, alice.Token, map[string]any{
		"url": "https://novelbin.com/b/test-novel",
	})
	assertStatus(t, patchResp, http.StatusOK)

	createChapterWithTitle(t, env.handler, alice.Token, novel.ID, 1, "Chapter 1: First Steps")
	createChapterWithTitle(t, env.handler, alice.Token, novel.ID, 2, "Chapter 2: The Journey")

	resp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/update-preview", alice.Token, nil)
	if resp.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", resp.Code, resp.Body.String())
	}

	var preview struct {
		CurrentChapters int `json:"currentChapters"`
		TotalChapters   int `json:"totalChapters"`
		NewChapters     int `json:"newChapters"`
		FirstNewChapter int `json:"firstNewChapter"`
		LastNewChapter  int `json:"lastNewChapter"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &preview); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if preview.NewChapters != 0 {
		t.Errorf("newChapters: got %d, want 0", preview.NewChapters)
	}
	if preview.FirstNewChapter != 0 || preview.LastNewChapter != 0 {
		t.Errorf("first/last new chapter should be 0 when up to date, got %d/%d", preview.FirstNewChapter, preview.LastNewChapter)
	}
}

func TestUpdateFromUrlRangeIncludesEndChapter(t *testing.T) {
	var archiveItems []string
	for n := 1; n <= 13; n++ {
		archiveItems = append(archiveItems, fmt.Sprintf(`<li><a href="https://novelbin.com/b/test-novel/chapter-%d">Chapter %d</a></li>`, n, n))
	}
	archiveHTML := `<ul class="list-chapter">` + strings.Join(archiveItems, "") + `</ul>`

	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, archiveHTML)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinChapterHTML)
		default:
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprint(w, testNovelbinHTML)
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	oldQueue := env.server.downloadQueue
	env.server.downloadQueue = make(chan string, 1000)
	close(oldQueue)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-update-range@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")
	patchResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID, alice.Token, map[string]any{
		"url": "https://novelbin.com/b/test-novel",
	})
	assertStatus(t, patchResp, http.StatusOK)

	for n := 1; n <= 9; n++ {
		createChapterWithTitle(t, env.handler, alice.Token, novel.ID, n, fmt.Sprintf("Chapter %d", n))
	}

	for _, tc := range []struct {
		name  string
		input map[string]any
		want  int
	}{
		{"all", map[string]any{}, 4},
		{"range 10-13", map[string]any{"startChapter": 10, "endChapter": 13}, 4},
		{"range 10-12", map[string]any{"startChapter": 10, "endChapter": 12}, 3},
	} {
		t.Run(tc.name, func(t *testing.T) {
			resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/update-from-url", alice.Token, tc.input)
			if resp.Code != http.StatusOK {
				t.Fatalf("expected 200, got %d: %s", resp.Code, resp.Body.String())
			}
			t.Logf("%s response: %s", tc.name, resp.Body.String())
			var result struct {
				PendingChapters int `json:"pendingChapters"`
			}
			decodeResponse(t, resp, &result)
			if result.PendingChapters != tc.want {
				t.Errorf("pendingChapters: got %d, want %d", result.PendingChapters, tc.want)
			}
		})
	}
}

func TestUpdateUrlPreviewRejectsNovelWithoutURL(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-update-nourl@example.com", "secret123", "Alice")
	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")

	resp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/update-preview", alice.Token, nil)
	if resp.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", resp.Code, resp.Body.String())
	}
}

func TestUpdateFromUrlUsesCacheFromPreview(t *testing.T) {
	var novelInfoRequests int
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li><li><a href="%s">Chapter 2: The Journey</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinChapterHTML))
		default:
			novelInfoRequests++
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	oldQueue := env.server.downloadQueue
	env.server.downloadQueue = make(chan string, 1000)
	close(oldQueue)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-cache-test@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")
	patchResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID, alice.Token, map[string]any{
		"url": "https://novelbin.com/b/test-novel",
	})
	assertStatus(t, patchResp, http.StatusOK)

	createChapter(t, env.handler, alice.Token, novel.ID, 1)

	novelInfoRequests = 0

	previewResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/update-preview", alice.Token, nil)
	if previewResp.Code != http.StatusOK {
		t.Fatalf("preview: expected 200, got %d: %s", previewResp.Code, previewResp.Body.String())
	}
	if novelInfoRequests != 1 {
		t.Fatalf("after preview: expected 1 novel info request, got %d", novelInfoRequests)
	}

	updateResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/update-from-url", alice.Token, map[string]any{})
	if updateResp.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", updateResp.Code, updateResp.Body.String())
	}
	if novelInfoRequests != 1 {
		t.Errorf("after update: expected still 1 novel info request (cache hit), got %d", novelInfoRequests)
	}

	var result struct {
		PendingChapters int `json:"pendingChapters"`
	}
	decodeResponse(t, updateResp, &result)
	if result.PendingChapters != 1 {
		t.Errorf("pendingChapters: got %d, want 1", result.PendingChapters)
	}
}

func TestUpdateFromUrlFallsBackWithoutPreview(t *testing.T) {
	var novelInfoRequests int
	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/cover.jpg"):
			w.Header().Set("Content-Type", "image/jpeg")
			_, _ = w.Write([]byte("fake-jpeg"))
		case strings.HasSuffix(r.URL.Path, "/ajax/chapter-archive"):
			chapterURL := "https://novelbin.com/b/test-novel/chapter-1"
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = fmt.Fprintf(w, `<ul class="list-chapter"><li><a href="%s">Chapter 1: First Steps</a></li><li><a href="%s">Chapter 2: The Journey</a></li></ul>`, chapterURL, chapterURL)
		case strings.Contains(r.URL.Path, "/chapter-"):
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinChapterHTML))
		default:
			novelInfoRequests++
			w.Header().Set("Content-Type", "text/html; charset=utf-8")
			_, _ = w.Write([]byte(testNovelbinHTML))
		}
	}))
	defer mock.Close()

	rewrites := map[string]string{"novelbin.com": mock.URL}
	transport := &hostRewritingTransport{rewrites: rewrites}
	client := noveldownloader.NewHTTPClientWithTransport(transport)

	env := newAPITestEnv(t)
	oldQueue := env.server.downloadQueue
	env.server.downloadQueue = make(chan string, 1000)
	close(oldQueue)
	env.server.DownloaderFactory = func() *noveldownloader.Downloader {
		return noveldownloader.NewDownloaderWithClient(client)
	}

	alice := registerUser(t, env.handler, "alice-fallback-test@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Test", "en", "es")
	patchResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID, alice.Token, map[string]any{
		"url": "https://novelbin.com/b/test-novel",
	})
	assertStatus(t, patchResp, http.StatusOK)

	createChapter(t, env.handler, alice.Token, novel.ID, 1)

	novelInfoRequests = 0

	updateResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/update-from-url", alice.Token, map[string]any{})
	if updateResp.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d: %s", updateResp.Code, updateResp.Body.String())
	}
	if novelInfoRequests != 1 {
		t.Errorf("without preview: expected 1 novel info request (fallback scrape), got %d", novelInfoRequests)
	}
}

func createChapterWithTitle(t *testing.T, handler http.Handler, token, novelID string, order int, title string) {
	t.Helper()
	resp := doJSONRequest(t, handler, http.MethodPost, "/api/db/novels/"+novelID+"/chapters", token, map[string]any{
		"chapterOrder":    order,
		"title":           title,
		"originalContent": "Texto original",
	})
	assertStatus(t, resp, http.StatusCreated)
}
