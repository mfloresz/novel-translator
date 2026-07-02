// Simple test to verify deterministicBookID works correctly
package epubexport

import (
	"strings"
	"testing"
)

func TestDeterministicBookID(t *testing.T) {
	meta1 := EpubMetadata{
		Title:     "The Lord of the Rings",
		Author:    "J.R.R. Tolkien",
		Language:  "es",
		Publisher: "NovelTranslator",
		Series:    "The Lord of the Rings",
		Number:    "1",
	}
	meta2 := EpubMetadata{
		Title:     "The Lord of the Rings",
		Author:    "J.R.R. Tolkien",
		Language:  "es",
		Publisher: "NovelTranslator",
		Series:    "The Lord of the Rings",
		Number:    "1",
	}

	id1 := deterministicBookID(meta1)
	id2 := deterministicBookID(meta2)

	if id1 != id2 {
		t.Fatalf("Expected same IDs, got %s and %s", id1, id2)
	}

	if !strings.HasPrefix(id1, "book-") {
		t.Fatalf("Expected book-* prefix, got %s", id1)
	}

	if len(id1) <= len("book-") {
		t.Fatalf("ID too short: %s", id1)
	}
}
