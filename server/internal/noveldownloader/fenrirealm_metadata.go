package noveldownloader

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"

	"github.com/PuerkitoBio/goquery"
)

// fenrirSeriesAPIResponse maps the JSON returned by
// GET /api/new/v2/series/{slug}.
type fenrirSeriesAPIResponse struct {
	ID          int                    `json:"id"`
	Title       string                 `json:"title"`
	Slug        string                 `json:"slug"`
	AltTitle    string                 `json:"alt_title"`
	Status      string                 `json:"status"`
	Description string                 `json:"description"`
	Type        string                 `json:"type"`
	Cover       string                 `json:"cover"`
	CoverData   string                 `json:"cover_data_url"`
	User        *fenrirUserInfo        `json:"user,omitempty"`
	Genres      []fenrirGenreTag       `json:"genres,omitempty"`
	Tags        []fenrirGenreTag       `json:"tags,omitempty"`
	Stats       map[string]interface{} `json:"stats,omitempty"`
	Notices     []interface{}          `json:"notices,omitempty"`
}

type fenrirUserInfo struct {
	Username string `json:"username"`
	Name     string `json:"name"`
}

type fenrirGenreTag struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
	Slug string `json:"slug"`
}

// fenrirChapterItem maps one element of the array returned by
// GET /api/new/v2/series/{slug}/chapters.
type fenrirChapterItem struct {
	ID       int    `json:"id"`
	Slug     string `json:"slug"`
	Name     string `json:"name"`
	Title    string `json:"title"`
	Number   int    `json:"number"`
	Type     string `json:"type"`
	Locked   map[string]interface{} `json:"locked,omitempty"`
	Bought   map[string]interface{} `json:"bought,omitempty"`
}

// fenrirExtractSlug extracts the series slug from a fenrirealm.com series URL.
// Expected input: https://fenrirealm.com/series/absolute-regression
// Returns: "absolute-regression"
func fenrirExtractSlug(pageURL string) (string, error) {
	u, err := url.Parse(pageURL)
	if err != nil {
		return "", fmt.Errorf("parsing URL: %w", err)
	}
	// Path should be /series/{slug} or /series/{slug}/...
	parts := strings.Split(strings.Trim(u.Path, "/"), "/")
	if len(parts) < 2 || parts[0] != "series" {
		return "", fmt.Errorf("unexpected URL path: %s", u.Path)
	}
	return parts[1], nil
}

func (p *FenrirRealmParser) GetNovelInfo(ctx context.Context, client HTTPClient, pageURL string) (*NovelInfo, error) {
	slug, err := fenrirExtractSlug(pageURL)
	if err != nil {
		return nil, fmt.Errorf("extracting slug: %w", err)
	}

	// 1. Fetch series metadata.
	metaURL := fmt.Sprintf("https://fenrirealm.com/api/new/v2/series/%s", slug)
	metaBody, err := client.Fetch(ctx, metaURL)
	if err != nil {
		return nil, fmt.Errorf("fetching series metadata: %w", err)
	}

	var meta fenrirSeriesAPIResponse
	if err := json.Unmarshal(metaBody, &meta); err != nil {
		return nil, fmt.Errorf("parsing series metadata: %w", err)
	}

	// 2. Fetch chapter list.
	chaptersURL := fmt.Sprintf("https://fenrirealm.com/api/new/v2/series/%s/chapters", slug)
	chBody, err := client.Fetch(ctx, chaptersURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapter list: %w", err)
	}

	var chapterItems []fenrirChapterItem
	if err := json.Unmarshal(chBody, &chapterItems); err != nil {
		return nil, fmt.Errorf("parsing chapter list: %w", err)
	}

	// 3. Build chapter URLs.
	chapters := make([]ChapterURL, 0, len(chapterItems))
	for _, ch := range chapterItems {
		// Chapter URL: https://fenrirealm.com/series/{slug}/{chapterSlug}
		chURL := fmt.Sprintf("https://fenrirealm.com/series/%s/%s", slug, ch.Slug)
		title := ch.Name
		if title == "" {
			title = ch.Title
		}
		chapters = append(chapters, ChapterURL{
			URL:   chURL,
			Title: CleanTitle(title),
		})
	}

	// 4. Build cover URL.
	coverURL := ""
	if meta.Cover != "" {
		coverURL = "https://fenrirealm.com/" + strings.TrimPrefix(meta.Cover, "/")
	}

	// 5. Determine author from the user field.
	author := ""
	if meta.User != nil {
		author = meta.User.Username
	}

	// 6. Build description (strip HTML tags or keep as-is for the backend).
	description := strings.TrimSpace(meta.Description)

	return &NovelInfo{
		Title:       meta.Title,
		Author:      author,
		Description: description,
		CoverURL:    coverURL,
		SourceURL:   pageURL,
		Chapters:    chapters,
	}, nil
}

func (p *FenrirRealmParser) GetChapterURLs(ctx context.Context, client HTTPClient, _ *goquery.Document, pageURL string) ([]ChapterURL, error) {
	slug, err := fenrirExtractSlug(pageURL)
	if err != nil {
		return nil, fmt.Errorf("extracting slug: %w", err)
	}

	chaptersURL := fmt.Sprintf("https://fenrirealm.com/api/new/v2/series/%s/chapters", slug)
	chBody, err := client.Fetch(ctx, chaptersURL)
	if err != nil {
		return nil, fmt.Errorf("fetching chapter list: %w", err)
	}

	var chapterItems []fenrirChapterItem
	if err := json.Unmarshal(chBody, &chapterItems); err != nil {
		return nil, fmt.Errorf("parsing chapter list: %w", err)
	}

	chapters := make([]ChapterURL, 0, len(chapterItems))
	for _, ch := range chapterItems {
		chURL := fmt.Sprintf("https://fenrirealm.com/series/%s/%s", slug, ch.Slug)
		title := ch.Name
		if title == "" {
			title = ch.Title
		}
		chapters = append(chapters, ChapterURL{
			URL:   chURL,
			Title: CleanTitle(title),
		})
	}

	return chapters, nil
}


