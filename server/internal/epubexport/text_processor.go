package epubexport

import (
	"regexp"
	"strings"
)

var (
	reBoldItalic = regexp.MustCompile(`\*\*\*([^*\n]+)\*\*\*`)
	reBold       = regexp.MustCompile(`\*\*([^*\n]+)\*\*`)
	reItalic     = regexp.MustCompile(`\*([^*\n]+)\*`)
	reUnderline  = regexp.MustCompile(`_([^_\n]+)_`)
	reSeparator  = regexp.MustCompile(`(?m)^[\s]*[-]{3,}[\s]*$|(?m)^[\s]*[*]{3,}[\s]*$`)
)

func escapeXML(input string) string {
	r := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		"\"", "&quot;",
		"'", "&apos;",
	)
	return r.Replace(input)
}

func ProcessChapter(content string) string {
	txt := strings.ReplaceAll(content, "\r\n", "\n")

	txt = reBoldItalic.ReplaceAllString(txt, "<b><i>$1</i></b>")
	txt = reBold.ReplaceAllString(txt, "<b>$1</b>")
	txt = reItalic.ReplaceAllString(txt, "<i>$1</i>")
	txt = reUnderline.ReplaceAllString(txt, "<i>$1</i>")

	txt = reSeparator.ReplaceAllString(txt, "<hr/>")

	blocks := strings.Split(txt, "\n\n")
	var out []string
	for _, block := range blocks {
		trimmed := strings.TrimSpace(block)
		if trimmed == "" {
			continue
		}
		if strings.HasPrefix(trimmed, "<") {
			out = append(out, trimmed)
		} else {
			lines := strings.Split(trimmed, "\n")
			var cleanLines []string
			for _, line := range lines {
				l := strings.TrimSpace(line)
				if l != "" {
					cleanLines = append(cleanLines, l)
				}
			}
			out = append(out, "<p>"+strings.Join(cleanLines, "<br/>")+"</p>")
		}
	}
	return strings.Join(out, "\n")
}
