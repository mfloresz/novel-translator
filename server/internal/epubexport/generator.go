package epubexport

import (
	"archive/zip"
	"bytes"
	"fmt"
	"io"
	"strings"
	"time"
)

type EpubMetadata struct {
	Title       string
	Author      string
	Description string
	Language    string
	Publisher   string
	Series      string
	Number      string
}

type ChapterData struct {
	Title   string
	Content string
}

func deterministicBookID(meta EpubMetadata) string {
	hash := meta.Title + meta.Author + meta.Language + meta.Publisher + meta.Series + meta.Number
	return fmt.Sprintf("book-%d", hashFunc(hash))
}

func hashFunc(input string) int64 {
	h := int64(0)
	for _, b := range []byte(input) {
		h = h*31 + int64(b)
	}
	if h == 0 {
		h = 1
	} else if h < 0 {
		h = -h
	}
	return h
}

func GenerateEpubFile(meta EpubMetadata, chapters []ChapterData, coverBytes []byte, coverMime string) ([]byte, error) {
	buf := new(bytes.Buffer)
	w := zip.NewWriter(buf)

	writeFile := func(name string, data []byte, compressed bool) error {
		method := zip.Deflate
		if !compressed {
			method = zip.Store
		}
		f, err := w.CreateHeader(&zip.FileHeader{
			Name:   name,
			Method: method,
		})
		if err != nil {
			return err
		}
		_, err = f.Write(data)
		return err
	}

	if err := writeFile("mimetype", []byte("application/epub+zip"), false); err != nil {
		return nil, err
	}
	if err := writeFile("META-INF/container.xml", []byte(containerXML), false); err != nil {
		return nil, err
	}
	if err := writeFile("META-INF/com.apple.ibooks.display-options.xml", []byte(ibooksDisplayXML), false); err != nil {
		return nil, err
	}
	if err := writeFile("OEBPS/css/styles.css", []byte(defaultCSS), false); err != nil {
		return nil, err
	}

	hasCover := len(coverBytes) > 0
	coverMimeStr := coverMime
	if coverMimeStr == "" {
		coverMimeStr = "image/jpeg"
	}
	coverExt := mimeToExt(coverMimeStr)

	if hasCover {
		if err := writeFile("OEBPS/cover"+coverExt, coverBytes, false); err != nil {
			return nil, err
		}
		// Create XHTML cover page
		coverXhtml := buildCoverXHTML(coverExt, coverMimeStr)
		if err := writeFile("OEBPS/cover.xhtml", []byte(coverXhtml), false); err != nil {
			return nil, err
		}
	}

	if err := writeFile("OEBPS/toc.ncx", []byte(buildTocNCX(meta, chapters, hasCover)), false); err != nil {
		return nil, err
	}
	if err := writeFile("OEBPS/toc.xhtml", []byte(buildTocXHTML(meta, chapters)), false); err != nil {
		return nil, err
	}

	for i, ch := range chapters {
		filename := fmt.Sprintf("OEBPS/chapter%d.xhtml", i+1)
		html := buildChapterXHTML(ch)
		if err := writeFile(filename, []byte(html), false); err != nil {
			return nil, err
		}
	}

	if err := writeFile("OEBPS/content.opf", []byte(buildContentOPF(meta, chapters, hasCover, coverMimeStr, coverExt)), false); err != nil {
		return nil, err
	}

	if err := w.Close(); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func buildChapterXHTML(ch ChapterData) string {
	body := ProcessChapter(ch.Content)
	return fmt.Sprintf(`<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>%s</title>
  <link rel="stylesheet" type="text/css" href="css/styles.css"/>
</head>
<body>
  <h1 class="chapter-title">%s</h1>
  %s
</body>
</html>`, escapeXML(ch.Title), escapeXML(ch.Title), body)
}

// descriptionToEscapedHTML converts a plain-text/blank-line-separated
// description into escaped HTML paragraphs embedded inside dc:description.
// This mirrors the de-facto convention used by Calibre and most EPUB
// tooling/catalogs: line breaks alone are not preserved by HTML renderers,
// but real <p> markup (escaped so it stays valid XML text content) is.
func descriptionToEscapedHTML(desc string) string {
	normalized := strings.ReplaceAll(desc, "\r\n", "\n")
	paragraphs := strings.Split(normalized, "\n\n")
	var parts []string
	for _, p := range paragraphs {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		lines := strings.Split(p, "\n")
		var cleanLines []string
		for _, l := range lines {
			l = strings.TrimSpace(l)
			if l != "" {
				cleanLines = append(cleanLines, l)
			}
		}
		if len(cleanLines) == 0 {
			continue
		}
		parts = append(parts, "<p>"+strings.Join(cleanLines, "<br/>")+"</p>")
	}
	return escapeXML(strings.Join(parts, ""))
}

func buildCoverXHTML(coverExt, coverMime string) string {
	return fmt.Sprintf(`<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Cover</title>
  <style type="text/css">
    body { margin: 0; padding: 0; }
    img { max-width: 100%%; height: auto; display: block; }
  </style>
</head>
<body>
  <div id="cover-image">
    <img src="cover%s" alt="Cover" />
  </div>
</body>
</html>`, coverExt)
}

func buildContentOPF(meta EpubMetadata, chapters []ChapterData, hasCover bool, coverMime, coverExt string) string {
	bookID := deterministicBookID(meta)
	now := time.Now().UTC().Format("2006-01-02T15:04:05Z")

	var b strings.Builder
	b.WriteString(fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xml:lang="%s" xmlns="http://www.idpf.org/2007/opf" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf" xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata" xmlns:dcterms="http://purl.org/dc/terms/">
    <dc:identifier id="book-id">%s</dc:identifier>
    <dc:title>%s</dc:title>
    <dc:creator opf:role="aut" opf:file-as="%s">%s</dc:creator>
    <dc:publisher>%s</dc:publisher>
    <dc:language>%s</dc:language>
    <dc:date>%s</dc:date>
    <meta property="dcterms:modified">%s</meta>
    <meta name="calibre:title_sort" content="%s"/>`,
		escapeXML(meta.Language),
		escapeXML(bookID),
		escapeXML(meta.Title),
		escapeXML(meta.Author),
		escapeXML(meta.Author),
		escapeXML(meta.Publisher),
		escapeXML(meta.Language),
		now[:10],
		now,
		escapeXML(meta.Title),
	))

	if meta.Description != "" {
		b.WriteString(fmt.Sprintf("\n    <dc:description>%s</dc:description>", descriptionToEscapedHTML(meta.Description)))
	}

	if meta.Series != "" {
		posStr := meta.Number
		if posStr == "" {
			posStr = "1"
		}
		b.WriteString(fmt.Sprintf(`
    <meta property="belongs-to-collection" id="collection">%s</meta>
    <meta refines="#collection" property="collection-type">series</meta>
    <meta refines="#collection" property="group-position">%s</meta>
    <meta name="calibre:series" content="%s"/>
    <meta name="calibre:series_index" content="%s"/>`,
			escapeXML(meta.Series),
			escapeXML(posStr),
			escapeXML(meta.Series),
			escapeXML(posStr),
		))
	}

	b.WriteString(`
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="css" href="css/styles.css" media-type="text/css"/>
    <item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>`)

	if hasCover {
		b.WriteString(fmt.Sprintf(`
    <item id="cover-image" href="cover%s" media-type="%s" properties="cover-image"/>
    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>`, coverExt, coverMime))
	}

	for i := range chapters {
		b.WriteString(fmt.Sprintf(`
    <item id="chapter%d" href="chapter%d.xhtml" media-type="application/xhtml+xml"/>`, i+1, i+1))
	}

	b.WriteString(`
  </manifest>
  <spine toc="ncx">`)

	if hasCover {
		b.WriteString(`
    <itemref idref="cover"/>`)
	}

	for i := range chapters {
		b.WriteString(fmt.Sprintf(`
    <itemref idref="chapter%d"/>`, i+1))
	}

	b.WriteString(`
  </spine>
</package>`)
	return b.String()
}

func buildTocNCX(meta EpubMetadata, chapters []ChapterData, hasCover bool) string {
	bookID := deterministicBookID(meta)
	playOrder := 1

	var b strings.Builder
	b.WriteString(fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xml:lang="%s" xmlns="http://www.daisy.org/z3986/2005/ncx/">
  <head>
    <meta name="dtb:uid" content="%s"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>%s</text>
  </docTitle>
  <navMap>`, escapeXML(meta.Language), escapeXML(bookID), escapeXML(meta.Title)))

	if hasCover {
		b.WriteString(fmt.Sprintf(`
    <navPoint id="nav0" playOrder="%d">
      <navLabel>
        <text>Cover</text>
      </navLabel>
      <content src="cover.xhtml"/>
    </navPoint>`, playOrder))
		playOrder++
	}

	for i, ch := range chapters {
		b.WriteString(fmt.Sprintf(`
    <navPoint id="nav%d" playOrder="%d">
      <navLabel>
        <text>%s</text>
      </navLabel>
      <content src="chapter%d.xhtml"/>
    </navPoint>`, i+1, playOrder, escapeXML(ch.Title), i+1))
		playOrder++
	}

	b.WriteString(`
  </navMap>
</ncx>`)
	return b.String()
}

func buildTocXHTML(meta EpubMetadata, chapters []ChapterData) string {
	var b strings.Builder
	b.WriteString(fmt.Sprintf(`<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title>%s</title>
  </head>
  <body>
    <nav epub:type="toc">
      <h1>Table of Contents</h1>
      <ol>`, escapeXML(meta.Title)))

	for i, ch := range chapters {
		b.WriteString(fmt.Sprintf(`
        <li><a href="chapter%d.xhtml">%s</a></li>`, i+1, escapeXML(ch.Title)))
	}

	b.WriteString(`
      </ol>
    </nav>
  </body>
</html>`)
	return b.String()
}

func mimeToExt(mime string) string {
	if strings.Contains(mime, "jpeg") || strings.Contains(mime, "jpg") {
		return ".jpg"
	}
	if strings.Contains(mime, "png") {
		return ".png"
	}
	if strings.Contains(mime, "webp") {
		return ".webp"
	}
	return ".jpg"
}

func DetectImageMime(data []byte) string {
	if len(data) < 4 {
		return "image/jpeg"
	}
	if data[0] == 0xFF && data[1] == 0xD8 {
		return "image/jpeg"
	}
	if data[0] == 0x89 && data[1] == 0x50 && data[2] == 0x4E && data[3] == 0x47 {
		return "image/png"
	}
	if data[0] == 0x52 && data[1] == 0x49 && data[2] == 0x46 && data[3] == 0x46 {
		return "image/webp"
	}
	return "image/jpeg"
}

func ReadCloserToBytes(r io.Reader) ([]byte, error) {
	return io.ReadAll(r)
}

const containerXML = `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`

const ibooksDisplayXML = `<?xml version="1.0" encoding="UTF-8"?>
<display_options>
  <platform name="*">
    <option name="specified-fonts">true</option>
  </platform>
</display_options>`

const defaultCSS = `* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: "Libre Baskerville", "Times New Roman", serif;
  font-size: 1em;
  line-height: 1.6;
  margin: 0 auto;
  max-width: 100%;
  padding: 0;
  text-align: justify;
  color: #333;
  background: #fff;
}

h1 {
  font-size: 1.5em;
  font-weight: bold;
  text-align: center;
  margin: 2em 0 1em 0;
  line-height: 1.2;
}

h1.chapter-title {
  page-break-before: always;
}

h2 {
  font-size: 1.25em;
  font-weight: bold;
  margin: 1.5em 0 0.5em 0;
  text-align: left;
}

h3 {
  font-size: 1.1em;
  font-weight: bold;
  margin: 1.25em 0 0.5em 0;
  text-align: left;
}

p {
  text-indent: 1.5em;
  margin: 0 0 1em 0;
  text-align: justify;
  orphans: 2;
  widows: 2;
}

p:first-of-type {
  text-indent: 0;
}

img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 1em auto;
  border-radius: 4px;
}

.titlepage {
  text-align: center;
  page-break-after: always;
  padding: 2em 1em;
}

.cover {
  text-align: center;
  page-break-after: always;
  padding: 2em 1em;
}

hr {
  border: none;
  margin: 2.75em 0;
  text-align: center;
  color: #57544c;
  font-size: 1.1em;
  letter-spacing: 0.4em;
  opacity: 0.6;
  page-break-after: avoid;
}

hr::after {
  content: "\2767  \2726  \2767";
}

blockquote {
  margin: 1em 2em;
  font-style: italic;
  border-left: 4px solid #ccc;
  padding-left: 1em;
}

em, i {
  font-style: italic;
}

strong, b {
  font-weight: bold;
}

ul, ol {
  margin: 1em 0;
  padding-left: 2em;
}

li {
  margin-bottom: 0.5em;
}

code {
  font-family: "Courier New", monospace;
  background: #f5f5f5;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}

pre {
  font-family: "Courier New", monospace;
  background: #f5f5f5;
  padding: 1em;
  border-radius: 4px;
  margin: 1em 0;
  overflow-x: auto;
  white-space: pre-wrap;
}

a {
  color: #0066cc;
  text-decoration: underline;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
}

th, td {
  border: 1px solid #ccc;
  padding: 0.5em;
  text-align: left;
}

th {
  background: #f5f5f5;
  font-weight: bold;
}

.page-break {
  page-break-before: always;
}

@media print {
  body {
    font-size: 12pt;
  }
  h1 {
    font-size: 18pt;
  }
  p {
    text-indent: 1.5em;
  }
}`
