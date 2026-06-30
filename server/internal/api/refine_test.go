package api

import (
	"testing"

	"translator-server/internal/ai"
)

func TestBuildRefineChunksUsesEditableLinesWithOverlap(t *testing.T) {
	original := "o1\no2\no3\no4\no5"
	translation := "t1\nt2\nt3\nt4\nt5"

	chunks := buildRefineChunks(original, translation, 2, 1)
	if len(chunks) != 3 {
		t.Fatalf("expected 3 chunks, got %d", len(chunks))
	}

	if chunks[1].TranslationChunk != "t3\nt4" {
		t.Fatalf("unexpected editable chunk: %q", chunks[1].TranslationChunk)
	}
	if chunks[1].TranslationContext != "t2\nt3\nt4\nt5" {
		t.Fatalf("unexpected translation context: %q", chunks[1].TranslationContext)
	}
	if chunks[1].OriginalContext != "o2\no3\no4\no5" {
		t.Fatalf("unexpected original context: %q", chunks[1].OriginalContext)
	}
}

func TestApplyRefineEditsOnlyAppliesExactUniqueMatches(t *testing.T) {
	text := "La casa era roja.\nLa casa era roja.\nEl cielo era azul."
	edits := []ai.RefineEdit{
		{Original: "La casa era roja.", Replacement: "La casa estaba roja."},
		{Original: "El cielo era azul.", Replacement: "El cielo estaba azul."},
		{Original: "No existe.", Replacement: "No existía."},
	}

	updated, applied := applyRefineEdits(text, edits)
	if applied != 1 {
		t.Fatalf("expected 1 applied edit, got %d", applied)
	}
	want := "La casa era roja.\nLa casa era roja.\nEl cielo estaba azul."
	if updated != want {
		t.Fatalf("unexpected text:\nwant: %q\n got: %q", want, updated)
	}
}
