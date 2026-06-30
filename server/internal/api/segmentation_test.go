package api

import (
	"strings"
	"testing"
	"unicode/utf8"

	"translator-server/internal/store"
)

func TestBuildSegmentsPreservesNormalizedSourceAndUnicode(t *testing.T) {
	text := "Primer párrafo con emoji 😊 y acentos.\r\n\r\n" +
		strings.Repeat("Esta oración mantiene sentido completo antes del corte. ", 20) +
		"最后一句也不 debe romper caracteres multibyte。"

	segments := buildSegments(text, store.TranslationDefaults{
		AutoSegment:    true,
		ThresholdChars: 80,
		MaxChars:       120,
		MinChars:       40,
	})
	if len(segments) < 2 {
		t.Fatalf("expected multiple segments, got %d", len(segments))
	}

	var rebuilt strings.Builder
	for i, segment := range segments {
		if segment.Text == "" {
			t.Fatalf("segment %d is empty", i)
		}
		if !utf8.ValidString(segment.Text) {
			t.Fatalf("segment %d contains invalid utf-8: %q", i, segment.Text)
		}
		rebuilt.WriteString(segment.Text)
	}

	want := strings.ReplaceAll(text, "\r\n", "\n")
	want = strings.ReplaceAll(want, "\r", "\n")
	if got := rebuilt.String(); got != want {
		t.Fatalf("segments did not preserve source content\nwant: %q\n got: %q", want, got)
	}
}

func TestBuildSegmentsPrefersNaturalSentenceBoundaries(t *testing.T) {
	text := strings.Repeat("Uno dos tres cuatro cinco. ", 8) +
		"Nuevo párrafo empieza aquí y debe quedar completo.\n\n" +
		strings.Repeat("Otra frase clara para traducir sin cortes abruptos. ", 8)

	segments := buildSegments(text, store.TranslationDefaults{
		AutoSegment:    true,
		ThresholdChars: 50,
		MaxChars:       150,
		MinChars:       60,
	})
	if len(segments) < 2 {
		t.Fatalf("expected multiple segments, got %d", len(segments))
	}

	first := segments[0].Text
	if !(strings.HasSuffix(first, ". ") || strings.HasSuffix(first, "\n\n")) {
		t.Fatalf("expected first segment to end at a natural boundary, got suffix %q", first[max(0, len(first)-20):])
	}
}

func TestBuildSegmentsFallsBackToWordBoundary(t *testing.T) {
	text := strings.Repeat("palabra ", 40)
	segments := buildSegments(text, store.TranslationDefaults{
		AutoSegment:    true,
		ThresholdChars: 20,
		MaxChars:       35,
		MinChars:       10,
	})
	if len(segments) < 2 {
		t.Fatalf("expected multiple segments, got %d", len(segments))
	}

	for i, segment := range segments[:len(segments)-1] {
		if !strings.HasSuffix(segment.Text, " ") {
			t.Fatalf("segment %d should end on a word boundary, got %q", i, segment.Text)
		}
	}
}

func TestBuildSegmentsAssignsSequentialIndexes(t *testing.T) {
	segments := buildSegments(strings.Repeat("Frase corta. ", 80), store.TranslationDefaults{
		AutoSegment:    true,
		ThresholdChars: 20,
		MaxChars:       120,
		MinChars:       60,
	})
	if len(segments) < 2 {
		t.Fatalf("expected multiple segments, got %d", len(segments))
	}
	for i, segment := range segments {
		if segment.Index != i {
			t.Fatalf("segment %d has index %d, want %d", i, segment.Index, i)
		}
	}
}

func TestBuildSegmentsSingleSegmentWithoutAutoSegmentation(t *testing.T) {
	segments := buildSegments("Capítulo completo sin segmentación.", store.TranslationDefaults{
		AutoSegment:    false,
		ThresholdChars: 20,
		MaxChars:       10,
		MinChars:       5,
	})
	if len(segments) != 1 {
		t.Fatalf("expected 1 segment, got %d", len(segments))
	}
	if segments[0].Index != 0 {
		t.Fatalf("single segment index=%d, want 0", segments[0].Index)
	}
}

func TestBuildSegmentsSingleSegmentBelowThreshold(t *testing.T) {
	segments := buildSegments("Texto corto.", store.TranslationDefaults{
		AutoSegment:    true,
		ThresholdChars: 1000,
		MaxChars:       500,
		MinChars:       100,
	})
	if len(segments) != 1 {
		t.Fatalf("expected 1 segment, got %d", len(segments))
	}
	if segments[0].Index != 0 {
		t.Fatalf("single segment index=%d, want 0", segments[0].Index)
	}
}
