package api

import (
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"

	"translator-server/internal/store"
)

func buildSegments(text string, cfg store.TranslationDefaults) []chapterSegment {
	cleaned := strings.ReplaceAll(text, "\r\n", "\n")
	cleaned = strings.ReplaceAll(cleaned, "\r", "\n")
	maxChars := cfg.MaxChars
	if maxChars <= 0 {
		maxChars = store.DefaultTranslationDefaults.MaxChars
	}
	minChars := cfg.MinChars
	if minChars <= 0 {
		minChars = store.DefaultTranslationDefaults.MinChars
	}
	if minChars > maxChars {
		minChars = maxChars
	}
	threshold := cfg.ThresholdChars
	if threshold <= 0 {
		threshold = store.DefaultTranslationDefaults.ThresholdChars
	}

	charCount := utf8.RuneCountInString(cleaned)
	if !cfg.AutoSegment || charCount <= threshold || charCount <= maxChars {
		return []chapterSegment{{Index: 0, Text: cleaned, StartChar: 0, EndChar: len(cleaned)}}
	}

	segments := []chapterSegment{}
	cursor := 0
	index := 0
	for cursor < len(cleaned) {
		remainingText := cleaned[cursor:]
		remainingChars := utf8.RuneCountInString(remainingText)
		if remainingChars <= maxChars {
			segments = append(segments, chapterSegment{Index: index, Text: remainingText, StartChar: cursor, EndChar: len(cleaned)})
			break
		}

		target := cursor + byteIndexAtRuneOffset(remainingText, maxChars)
		minCut := cursor + byteIndexAtRuneOffset(remainingText, minChars)
		cut := findCutIndex(cleaned, target, minCut)
		if cut <= cursor || cut > len(cleaned) {
			cut = target
		}

		segments = append(segments, chapterSegment{Index: index, Text: cleaned[cursor:cut], StartChar: cursor, EndChar: cut})
		index++
		cursor = cut
	}
	return segments
}

func findCutIndex(text string, target, minByte int) int {
	if target >= len(text) {
		return len(text)
	}
	if target < minByte {
		target = minByte
	}
	runes, offsets := runeOffsets(text)
	if len(runes) == 0 {
		return 0
	}
	targetRune := runeIndexAtOrBefore(offsets, target)
	minRune := runeIndexAtOrAfter(offsets, minByte)
	if targetRune < minRune {
		targetRune = minRune
	}

	searchStart := max(0, targetRune-800)
	searchEnd := min(len(runes), targetRune+200)
	bestCut := 0
	bestScore := -1.0
	patterns := []struct {
		value    string
		priority float64
	}{
		{"\n\n", 12.0},
		{".\n", 11.0},
		{"?\n", 11.0},
		{"!\n", 11.0},
		{"。\n", 11.0},
		{"？\n", 11.0},
		{"！\n", 11.0},
		{". ", 10.0},
		{"? ", 10.0},
		{"! ", 10.0},
		{"。", 9.5},
		{"？", 9.5},
		{"！", 9.5},
		{"\n", 8.0},
		{".", 7.0},
		{"?", 7.0},
		{"!", 7.0},
		{"…", 6.5},
		{"; ", 4.0},
		{": ", 3.5},
		{", ", 2.0},
	}
	for i := searchStart; i < searchEnd; i++ {
		for _, pattern := range patterns {
			patternRunes := []rune(pattern.value)
			if !hasRunePrefix(runes[i:], patternRunes) {
				continue
			}
			cutRune := i + len(patternRunes)
			if cutRune < minRune || cutRune >= len(offsets) {
				continue
			}
			distance := absInt(targetRune - cutRune)
			proximity := 1.0 - min(float64(distance), 800.0)/800.0
			if cutRune > targetRune {
				proximity *= 0.9
			}
			score := pattern.priority * proximity
			if score > bestScore {
				bestScore = score
				bestCut = offsets[cutRune]
			}
		}
	}
	if bestCut > 0 {
		return bestCut
	}
	return findWordBoundary(text, target, minByte)
}

func byteIndexAtRuneOffset(text string, runeOffset int) int {
	if runeOffset <= 0 {
		return 0
	}
	count := 0
	for idx := range text {
		if count == runeOffset {
			return idx
		}
		count++
	}
	return len(text)
}

func runeOffsets(text string) ([]rune, []int) {
	runeCount := utf8.RuneCountInString(text)
	runes := make([]rune, 0, runeCount)
	offsets := make([]int, 0, runeCount+1)
	for idx, r := range text {
		offsets = append(offsets, idx)
		runes = append(runes, r)
	}
	offsets = append(offsets, len(text))
	return runes, offsets
}

func runeIndexAtOrBefore(offsets []int, byteOffset int) int {
	idx := sort.Search(len(offsets), func(i int) bool { return offsets[i] > byteOffset }) - 1
	if idx < 0 {
		return 0
	}
	if idx >= len(offsets) {
		return len(offsets) - 1
	}
	return idx
}

func runeIndexAtOrAfter(offsets []int, byteOffset int) int {
	idx := sort.SearchInts(offsets, byteOffset)
	if idx >= len(offsets) {
		return len(offsets) - 1
	}
	return idx
}

func hasRunePrefix(text, prefix []rune) bool {
	if len(prefix) > len(text) {
		return false
	}
	for i, r := range prefix {
		if text[i] != r {
			return false
		}
	}
	return true
}

func findWordBoundary(text string, target, minByte int) int {
	runes, offsets := runeOffsets(text)
	if len(runes) == 0 {
		return 0
	}
	targetRune := runeIndexAtOrBefore(offsets, target)
	minRune := runeIndexAtOrAfter(offsets, minByte)
	for i := targetRune; i >= minRune && i > 0; i-- {
		if unicode.IsSpace(runes[i-1]) {
			return offsets[i]
		}
	}
	for i := targetRune; i < len(runes); i++ {
		if unicode.IsSpace(runes[i]) {
			return offsets[i+1]
		}
	}
	return offsets[targetRune]
}

func absInt(value int) int {
	if value < 0 {
		return -value
	}
	return value
}
