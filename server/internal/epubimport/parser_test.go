package epubimport

import (
	"os"
	"strings"
	"testing"
)

func TestParseBasic(t *testing.T) {
	blob, err := os.ReadFile("../../test/epub.epub")
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	result, err := Parse(blob, "test.epub")
	if err != nil {
		t.Fatal("Parse failed:", err)
	}

	if result.Title == "" {
		t.Error("expected non-empty title")
	}
	if result.Author == "" {
		t.Error("expected non-empty author")
	}
	if result.Language == "" {
		t.Error("expected non-empty language")
	}
	if len(result.Chapters) == 0 {
		t.Fatal("expected at least one chapter")
	}

	for i, ch := range result.Chapters {
		if ch.Title == "" {
			t.Errorf("chapter %d: empty title", i+1)
		}
		if ch.Content == "" {
			t.Errorf("chapter %d: empty content", i+1)
		}
	}
}

func TestParseNCXTitles(t *testing.T) {
	blob, err := os.ReadFile("../../test/epub.epub")
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	result, err := Parse(blob, "test.epub")
	if err != nil {
		t.Fatal("Parse failed:", err)
	}

	hasChapterTitles := false
	hasNCXTitle := false
	for _, ch := range result.Chapters {
		lower := strings.ToLower(ch.Title)
		if strings.Contains(lower, "chapter") && strings.Contains(lower, "1") {
			hasChapterTitles = true
		}
		if ch.Title == "Contents" || ch.Title == "Copyright" || ch.Title == "Prologue" || ch.Title == "Epilogue" {
			hasNCXTitle = true
		}
	}
	if !hasChapterTitles {
		t.Error("expected at least one 'Chapter N' title from NCX")
	}
	if !hasNCXTitle {
		t.Error("expected NCX-based title like Contents/Copyright/Prologue/Epilogue")
	}
}

func TestParseCoverImage(t *testing.T) {
	blob, err := os.ReadFile("../../test/epub.epub")
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	result, err := Parse(blob, "test.epub")
	if err != nil {
		t.Fatal("Parse failed:", err)
	}

	if len(result.CoverBlob) == 0 {
		t.Error("expected non-empty cover blob")
	}
	if result.CoverMime == "" {
		t.Error("expected non-empty cover mime type")
	}
}

func TestParseMetadata(t *testing.T) {
	blob, err := os.ReadFile("../../test/epub.epub")
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	result, err := Parse(blob, "test.epub")
	if err != nil {
		t.Fatal("Parse failed:", err)
	}

	if result.Series != "Copper Lake" {
		t.Errorf("expected series 'Copper Lake', got %q", result.Series)
	}
	if result.Number != "3.0" {
		t.Errorf("expected number '3.0', got %q", result.Number)
	}
}
