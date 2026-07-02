package epubexport

import (
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"
)

var (
	reBoldItalic   = regexp.MustCompile(`\*\*\*([^*\n]+)\*\*\*`)
	reBold         = regexp.MustCompile(`\*\*([^*\n]+)\*\*`)
	reItalic       = regexp.MustCompile(`\*([^*\n]+)\*`)
	reUnderlineRaw = regexp.MustCompile(`_([^_\n]+)_`)

	reSeparator = regexp.MustCompile(`(?m)^[\s]*[-]{3,}[\s]*$|(?m)^[\s]*[*]{3,}[\s]*$`)

	reHeading3 = regexp.MustCompile(`(?m)^### (.+)$`)
	reHeading2 = regexp.MustCompile(`(?m)^## (.+)$`)
	reHeading1 = regexp.MustCompile(`(?m)^# (.+)$`)
	// Blockquote marker is matched against the *escaped* form of "> ", since
	// escapeXML runs first and turns every literal ">" into "&gt;".
	reBlockquote = regexp.MustCompile(`(?m)^&gt; ?(.*)$`)
	reListLine   = regexp.MustCompile(`^\s*[-*]\s+(.+)$`)

	reBlockTagPrefix = regexp.MustCompile(`^<(h[1-6]|blockquote|hr)`)
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

// applyInlineMarkdown converts inline emphasis markers within a single
// block/line. It's safe to run on strings that already contain block-level
// tags (<p>, <h1>, <li>, ...) because those tags never contain '*' or '_'.
func applyInlineMarkdown(s string) string {
	s = reBoldItalic.ReplaceAllString(s, "<b><i>$1</i></b>")
	s = reBold.ReplaceAllString(s, "<b>$1</b>")
	s = reItalic.ReplaceAllString(s, "<i>$1</i>")
	s = convertUnderlineItalics(s)
	return s
}

// convertUnderlineItalics turns _text_ into <i>text</i>, but only when the
// underscores sit at a word boundary. This avoids mangling snake_case
// identifiers/stat names (e.g. "hp_current", common in game-system web
// novels) into italics. Go's regexp (RE2) has no lookaround support, so the
// boundary check is done manually against the surrounding runes.
func convertUnderlineItalics(s string) string {
	matches := reUnderlineRaw.FindAllStringSubmatchIndex(s, -1)
	if matches == nil {
		return s
	}
	var b strings.Builder
	last := 0
	for _, m := range matches {
		start, end := m[0], m[1]
		contentStart, contentEnd := m[2], m[3]
		if start < last {
			continue
		}
		if !hasWordBoundaries(s, start, end) {
			continue
		}
		b.WriteString(s[last:start])
		b.WriteString("<i>")
		b.WriteString(s[contentStart:contentEnd])
		b.WriteString("</i>")
		last = end
	}
	b.WriteString(s[last:])
	return b.String()
}

func hasWordBoundaries(s string, start, end int) bool {
	if start > 0 {
		r, _ := utf8.DecodeLastRuneInString(s[:start])
		if isWordRune(r) {
			return false
		}
	}
	if end < len(s) {
		r, _ := utf8.DecodeRuneInString(s[end:])
		if isWordRune(r) {
			return false
		}
	}
	return true
}

func isWordRune(r rune) bool {
	return unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_'
}

// convertListRuns turns "- item" / "* item" lines into <li>item</li>, but
// only for runs of 2 or more consecutive marker lines. A single marker line
// on its own is much more likely to be dialogue punctuation (some
// translation styles use a plain "- " as a speech dash) than an actual list
// item, so it's left untouched to avoid eating the dash.
func convertListRuns(txt string) string {
	lines := strings.Split(txt, "\n")
	var out []string
	i := 0
	for i < len(lines) {
		m := reListLine.FindStringSubmatch(lines[i])
		if m == nil {
			out = append(out, lines[i])
			i++
			continue
		}
		var items []string
		j := i
		for j < len(lines) {
			mj := reListLine.FindStringSubmatch(lines[j])
			if mj == nil {
				break
			}
			items = append(items, mj[1])
			j++
		}
		if len(items) >= 2 {
			for _, it := range items {
				out = append(out, "<li>"+it+"</li>")
			}
		} else {
			out = append(out, lines[i])
		}
		i = j
	}
	return strings.Join(out, "\n")
}

func isLiOnlyBlock(trimmed string) bool {
	lines := strings.Split(trimmed, "\n")
	found := false
	for _, l := range lines {
		l = strings.TrimSpace(l)
		if l == "" {
			continue
		}
		if !strings.HasPrefix(l, "<li>") || !strings.HasSuffix(l, "</li>") {
			return false
		}
		found = true
	}
	return found
}

func ProcessChapter(content string) string {
	txt := strings.ReplaceAll(content, "\r\n", "\n")

	// Escape entities before recognizing any markdown structure. None of the
	// markdown delimiters below (#, >, -, *, _) are affected by XML escaping
	// except ">" (blockquote), which is handled by matching its escaped form
	// ("&gt;") further down. This guarantees the output is always
	// well-formed XML regardless of what the source text contains.
	txt = escapeXML(txt)

	// Block-level structure is extracted first, on the raw (still
	// un-emphasized) text, so inline markdown never eats a "- "/"* " list
	// marker or a "# " heading marker.
	txt = reHeading3.ReplaceAllString(txt, "<h3>$1</h3>")
	txt = reHeading2.ReplaceAllString(txt, "<h2>$1</h2>")
	txt = reHeading1.ReplaceAllString(txt, "<h1>$1</h1>")
	txt = reBlockquote.ReplaceAllString(txt, "<blockquote>$1</blockquote>")
	txt = convertListRuns(txt)

	// Force the separator onto its own block, regardless of whether the
	// original text isolated it with blank lines. Without this, a scene
	// break glued to surrounding text would end up nested inside a <p>.
	txt = reSeparator.ReplaceAllString(txt, "\n\n<hr/>\n\n")

	blocks := strings.Split(txt, "\n\n")
	var out []string
	for _, block := range blocks {
		trimmed := strings.TrimSpace(block)
		if trimmed == "" {
			continue
		}

		if isLiOnlyBlock(trimmed) {
			lines := strings.Split(trimmed, "\n")
			var items []string
			for _, l := range lines {
				l = strings.TrimSpace(l)
				if l != "" {
					items = append(items, applyInlineMarkdown(l))
				}
			}
			out = append(out, "<ul>"+strings.Join(items, "")+"</ul>")
			continue
		}

		if reBlockTagPrefix.MatchString(trimmed) {
			out = append(out, applyInlineMarkdown(trimmed))
			continue
		}

		lines := strings.Split(trimmed, "\n")
		var cleanLines []string
		for _, line := range lines {
			l := strings.TrimSpace(line)
			if l != "" {
				cleanLines = append(cleanLines, applyInlineMarkdown(l))
			}
		}
		out = append(out, "<p>"+strings.Join(cleanLines, "<br/>")+"</p>")
	}
	return strings.Join(out, "\n")
}
