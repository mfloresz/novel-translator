package epubimport

import (
	"archive/zip"
	"bytes"
	"fmt"
	"mime"
	"path"
	"strings"

	html2md "github.com/JohannesKaufmann/html-to-markdown/v2"
)

func Parse(blob []byte, filename string) (*Result, error) {
	zr, err := zip.NewReader(bytes.NewReader(blob), int64(len(blob)))
	if err != nil {
		return nil, fmt.Errorf("invalid epub: %w", err)
	}

	containerXML, err := readZipFile(zr, "META-INF/container.xml")
	if err != nil {
		return nil, fmt.Errorf("missing META-INF/container.xml: %w", err)
	}
	opfPath, err := parseContainer(string(containerXML))
	if err != nil {
		return nil, err
	}
	opfXML, err := readZipFile(zr, opfPath)
	if err != nil {
		return nil, fmt.Errorf("missing OPF package %q: %w", opfPath, err)
	}

	metadata := parseMetadata(string(opfXML))
	manifest := parseManifest(string(opfXML))
	spine := parseSpine(string(opfXML))
	manifestMap := make(map[string]manifestItem, len(manifest))
	for _, item := range manifest {
		manifestMap[item.ID] = item
	}

	ncxNavPoints := parseNCXNavPoints(zr, opfPath, string(opfXML), manifestMap)

	unmatchedLabels := make(map[string]bool)
	for _, np := range ncxNavPoints {
		unmatchedLabels[np.Label] = true
	}

	result := &Result{
		Title:       firstNonEmpty(metadata["title"]...),
		Author:      firstNonEmpty(metadata["creator"]...),
		Description: normalizeDescription(firstNonEmpty(metadata["description"]...)),
		Language:    firstNonEmpty(metadata["language"]...),
		Series:      firstNonEmpty(metadata["series"]...),
		Number:      firstNonEmpty(metadata["number"]...),
	}
	if result.Title == "" {
		result.Title = strings.TrimSuffix(path.Base(filename), path.Ext(filename))
	}
	if result.Author == "" {
		result.Author = ""
	}

	coverID := parseCoverID(string(opfXML))
	if cover := findCover(manifest, coverID); cover != nil {
		coverPath := resolveZipPath(opfPath, cover.Href)
		if coverBlob, err := readZipFile(zr, coverPath); err == nil && len(coverBlob) > 0 {
			result.CoverBlob = coverBlob
			result.CoverMime = firstNonEmpty(cover.MediaType, mime.TypeByExtension(path.Ext(cover.Href)))
			if result.CoverMime == "" {
				result.CoverMime = "application/octet-stream"
			}
		}
	}

	ncxFragments := make(map[string]string)

	for _, idref := range spine {
		item, ok := manifestMap[idref]
		if !ok || !isHTMLItem(item) || shouldSkipManifestItem(item) {
			continue
		}
		htmlPath := resolveZipPath(opfPath, item.Href)
		htmlBlob, err := readZipFile(zr, htmlPath)
		if err != nil {
			continue
		}
		htmlString := removeScriptTags(string(htmlBlob))

		if len(unmatchedLabels) > 0 {
			remaining := make([]ncxNavPoint, 0, len(unmatchedLabels))
			for _, np := range ncxNavPoints {
				if unmatchedLabels[np.Label] {
					remaining = append(remaining, np)
				}
			}
			if fragments := splitChaptersFromNCXToFragments(htmlString, remaining); len(fragments) > 0 {
				for label := range fragments {
					delete(unmatchedLabels, label)
					ncxFragments[label] = fragments[label]
				}
				continue
			}
		}

		if chapters := splitChaptersFromHeadings(htmlString); len(chapters) >= 2 {
			result.Chapters = append(result.Chapters, chapters...)
			continue
		}

		markdown, err := html2md.ConvertString(htmlString)
		if err != nil {
			continue
		}
		markdown = normalizeMarkdown(markdown)
		markdown = stripLeadingMarkdownHeading(markdown)
		if markdown == "" || shouldSkipChapter(item, markdown, htmlString) {
			continue
		}
		title := extractTitle(htmlString, item.Href, len(result.Chapters)+len(ncxFragments)+1)
		for _, np := range ncxNavPoints {
			if _, exists := ncxFragments[np.Label]; !exists && unmatchedLabels[np.Label] && np.FilePath == htmlPath {
				title = np.Label
				delete(unmatchedLabels, np.Label)
				break
			}
		}
		result.Chapters = append(result.Chapters, Chapter{Title: title, Content: markdown})
	}

	for _, np := range ncxNavPoints {
		fragment, ok := ncxFragments[np.Label]
		if !ok {
			continue
		}
		markdown, err := html2md.ConvertString(fragment)
		if err != nil {
			continue
		}
		markdown = normalizeMarkdown(markdown)
		if markdown == "" {
			continue
		}
		result.Chapters = append(result.Chapters, Chapter{Title: np.Label, Content: markdown})
	}

	if len(result.Chapters) == 0 {
		return nil, fmt.Errorf("no se encontraron capítulos legibles en el EPUB")
	}
	return result, nil
}
