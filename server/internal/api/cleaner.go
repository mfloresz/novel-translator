package api

import (
	"regexp"
	"strings"
)

type CleanMode string

const (
	CleanModeRemoveAfter          CleanMode = "remove_after"
	CleanModeRemoveDuplicates     CleanMode = "remove_duplicates"
	CleanModeRemoveLine           CleanMode = "remove_line"
	CleanModeRemoveMultipleBlanks CleanMode = "remove_multiple_blanks"
	CleanModeSearchReplace        CleanMode = "search_replace"
)

type CleanOptions struct {
	Mode          CleanMode `json:"mode"`
	SearchText    string    `json:"searchText"`
	ReplaceText   string    `json:"replaceText"`
	CaseSensitive bool      `json:"caseSensitive"`
	UseRegex      bool      `json:"useRegex"`
}

type CleanResult struct {
	Original     string `json:"original"`
	Cleaned      string `json:"cleaned"`
	Changed      bool   `json:"changed"`
	RemovedLines int    `json:"removedLines"`
}

type CleanPreviewResult struct {
	ChapterTitle string `json:"chapterTitle"`
	CleanResult
}

func ApplyClean(text string, opts CleanOptions) CleanResult {
	original := text
	working := strings.ReplaceAll(text, "\r\n", "\n")
	working = strings.ReplaceAll(working, "\r", "\n")

	lines := strings.Split(working, "\n")
	lines = trimBlankEdges(lines)

	var processed []string
	switch opts.Mode {
	case CleanModeRemoveAfter:
		processed = applyRemoveAfter(lines, opts)
	case CleanModeRemoveDuplicates:
		processed = applyRemoveDuplicates(lines, opts)
	case CleanModeRemoveLine:
		processed = applyRemoveLine(lines, opts)
	case CleanModeRemoveMultipleBlanks:
		processed = normalizeBlankLines(lines)
	case CleanModeSearchReplace:
		processed = applySearchReplace(lines, opts)
	default:
		processed = lines
	}

	processed = trimBlankEdges(processed)
	cleaned := strings.Join(processed, "\n")

	return CleanResult{
		Original:     original,
		Cleaned:      cleaned,
		Changed:      cleaned != original,
		RemovedLines: len(lines) - len(processed),
	}
}

// ---------------------------------------------------------------------------
// Predicate builder: returns a function that tests a line for a match
// ---------------------------------------------------------------------------

func buildPredicate(searchText string, caseSensitive, useRegex bool) func(string) bool {
	if useRegex {
		pattern := searchText
		if !caseSensitive {
			pattern = "(?i)" + pattern
		}
		re, err := regexp.Compile(pattern)
		if err != nil {
			return func(line string) bool { return strings.Contains(line, searchText) }
		}
		return re.MatchString
	}

	if caseSensitive {
		return func(line string) bool { return strings.HasPrefix(line, searchText) }
	}

	needle := strings.ToLower(searchText)
	return func(line string) bool { return strings.HasPrefix(strings.ToLower(line), needle) }
}

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

func applyRemoveAfter(lines []string, opts CleanOptions) []string {
	if opts.SearchText == "" {
		return lines
	}
	pred := buildPredicate(opts.SearchText, opts.CaseSensitive, opts.UseRegex)
	for i, line := range lines {
		if pred(line) {
			return lines[:i]
		}
	}
	return lines
}

func applyRemoveDuplicates(lines []string, opts CleanOptions) []string {
	if opts.SearchText == "" {
		return lines
	}
	pred := buildPredicate(opts.SearchText, opts.CaseSensitive, opts.UseRegex)
	var matches []int
	for i, line := range lines {
		if pred(line) {
			matches = append(matches, i)
		}
	}
	if len(matches) <= 1 {
		return lines
	}
	remove := make(map[int]struct{}, len(matches)-1)
	for _, idx := range matches[:len(matches)-1] {
		remove[idx] = struct{}{}
	}
	out := make([]string, 0, len(lines)-len(remove))
	for i, line := range lines {
		if _, ok := remove[i]; !ok {
			out = append(out, line)
		}
	}
	return out
}

func applyRemoveLine(lines []string, opts CleanOptions) []string {
	if opts.SearchText == "" {
		return lines
	}
	pred := buildPredicate(opts.SearchText, opts.CaseSensitive, opts.UseRegex)
	out := make([]string, 0, len(lines))
	for _, line := range lines {
		if !pred(line) {
			out = append(out, line)
		}
	}
	return out
}

func normalizeBlankLines(lines []string) []string {
	out := make([]string, 0, len(lines))
	prevBlank := false
	for _, line := range lines {
		isBlank := strings.TrimSpace(line) == ""
		if isBlank {
			if !prevBlank {
				out = append(out, line)
			}
			prevBlank = true
		} else {
			out = append(out, line)
			prevBlank = false
		}
	}
	return out
}

func applySearchReplace(lines []string, opts CleanOptions) []string {
	if opts.SearchText == "" {
		return lines
	}
	replace := opts.ReplaceText

	if opts.UseRegex {
		pattern := opts.SearchText
		if !opts.CaseSensitive {
			pattern = "(?i)" + pattern
		}
		re, err := regexp.Compile(pattern)
		if err != nil {
			return applySplitReplace(lines, opts.SearchText, replace, opts.CaseSensitive)
		}
		out := make([]string, len(lines))
		for i, line := range lines {
			out[i] = re.ReplaceAllString(line, replace)
		}
		return out
	}

	return applySplitReplace(lines, opts.SearchText, replace, opts.CaseSensitive)
}

func applySplitReplace(lines []string, search, replace string, caseSensitive bool) []string {
	if !caseSensitive {
		out := make([]string, len(lines))
		for i, line := range lines {
			out[i] = caseInsensitiveReplace(line, search, replace)
		}
		return out
	}
	out := make([]string, len(lines))
	for i, line := range lines {
		out[i] = strings.ReplaceAll(line, search, replace)
	}
	return out
}

// ---------------------------------------------------------------------------
// Case-insensitive split/replace (matches TypeScript splitReplace)
// ---------------------------------------------------------------------------

func caseInsensitiveReplace(line, search, replace string) string {
	if search == "" {
		return line
	}
	lower := strings.ToLower(line)
	needle := strings.ToLower(search)

	var buf strings.Builder
	cursor := 0
	for {
		index := strings.Index(lower[cursor:], needle)
		if index == -1 {
			buf.WriteString(line[cursor:])
			break
		}
		buf.WriteString(line[cursor : cursor+index])
		buf.WriteString(replace)
		cursor += index + len(needle)
	}
	return buf.String()
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func trimBlankEdges(lines []string) []string {
	start := 0
	end := len(lines)
	for start < end && strings.TrimSpace(lines[start]) == "" {
		start++
	}
	for end > start && strings.TrimSpace(lines[end-1]) == "" {
		end--
	}
	if start == 0 && end == len(lines) {
		return lines
	}
	return lines[start:end]
}
