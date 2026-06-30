package epubimport

type Chapter struct {
	Title   string
	Content string
}

type Result struct {
	Title       string
	Author      string
	Description string
	Language    string
	Series      string
	Number      string
	CoverMime   string
	CoverBlob   []byte
	Chapters    []Chapter
}

type manifestItem struct {
	ID         string
	Href       string
	MediaType  string
	Properties string
}

type ncxNavPoint struct {
	Label    string
	FilePath string
	Anchor   string
}
