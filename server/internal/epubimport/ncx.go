package epubimport

import (
	"archive/zip"
	"html"
	"regexp"
	"strings"
)

var (
	reNCXNavPoint = regexp.MustCompile(`(?s)<navPoint[^>]*>.*?<navLabel>\s*<text>(.*?)</text>\s*</navLabel>.*?<content[^>]*src=["']([^"']+)["'].*?</navPoint>`)
	reSpineToc    = regexp.MustCompile(`<spine[^>]*toc=["']([^"']+)["']`)
)

func parseNCXNavPoints(zr *zip.Reader, opfPath, opfXML string, manifestMap map[string]manifestItem) []ncxNavPoint {
	tocID := extractFirstMatch(reSpineToc, opfXML)
	if tocID == "" {
		return nil
	}

	ncxItem, ok := manifestMap[tocID]
	if !ok {
		return nil
	}

	ncxPath := resolveZipPath(opfPath, ncxItem.Href)
	ncxBlob, err := readZipFile(zr, ncxPath)
	if err != nil {
		return nil
	}

	matches := reNCXNavPoint.FindAllStringSubmatch(string(ncxBlob), -1)
	var navPoints []ncxNavPoint
	for _, match := range matches {
		if len(match) < 3 {
			continue
		}
		label := normalizeInlineText(match[1])
		if label == "" {
			continue
		}
		src := html.UnescapeString(strings.TrimSpace(match[2]))

		var filePath, anchor string
		if idx := strings.IndexByte(src, '#'); idx >= 0 {
			filePath = resolveZipPath(opfPath, src[:idx])
			anchor = src[idx+1:]
		} else {
			filePath = resolveZipPath(opfPath, src)
		}

		navPoints = append(navPoints, ncxNavPoint{
			Label:    label,
			FilePath: filePath,
			Anchor:   anchor,
		})
	}

	return navPoints
}
