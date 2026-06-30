package noveldownloader

type NovelInfo struct {
	Title       string       `json:"title"`
	Author      string       `json:"author,omitempty"`
	Description string       `json:"description,omitempty"`
	CoverURL    string       `json:"cover_url,omitempty"`
	SourceURL   string       `json:"source_url"`
	Chapters    []ChapterURL `json:"chapters"`
}

type ChapterURL struct {
	URL   string `json:"url"`
	Title string `json:"title"`
}

type Chapter struct {
	Title     string `json:"title"`
	Content   string `json:"content,omitempty"`
	Markdown  string `json:"markdown,omitempty"`
	SourceURL string `json:"source_url"`
	Index     int    `json:"index"`
}

type DownloadRange struct {
	Start int
	End   int
}
