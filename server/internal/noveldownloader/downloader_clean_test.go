package noveldownloader

import (
	"testing"
)

func TestStripLeadingTitle(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		{
			name:     "single hash heading first line",
			input:    "# Chapter 1\n\nThis is the content.",
			expected: "This is the content.",
		},
		{
			name:     "double hash heading first line",
			input:    "## Chapter 1\n\nSome content here.",
			expected: "Some content here.",
		},
		{
			name:     "triple hash heading first line",
			input:    "### Chapter 1\n\nContent after heading.",
			expected: "Content after heading.",
		},
		{
			name:     "quadruple hash heading first line",
			input:    "#### Chapter 1\n\nContent here.",
			expected: "Content here.",
		},
		{
			name:     "no heading - plain text",
			input:    "This is the content.\n\nMore content.",
			expected: "This is the content.\n\nMore content.",
		},
		{
			name:     "heading in body, not first line",
			input:    "First paragraph.\n\n# Heading in body\n\nMore content.",
			expected: "First paragraph.\n\n# Heading in body\n\nMore content.",
		},
		{
			name:     "five hashes - not in range",
			input:    "##### Chapter 1\n\nContent.",
			expected: "##### Chapter 1\n\nContent.",
		},
		{
			name:     "empty content",
			input:    "",
			expected: "",
		},
		{
			name:     "only heading",
			input:    "# Chapter 1",
			expected: "",
		},
		{
			name:     "heading with leading newline",
			input:    "\n# Chapter 1\n\nContent.",
			expected: "Content.",
		},
		{
			name:     "hash without space - not a heading",
			input:    "#not a heading\n\nContent.",
			expected: "#not a heading\n\nContent.",
		},
		{
			name:     "single line no heading",
			input:    "Just one line of content.",
			expected: "Just one line of content.",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := stripLeadingTitle(tt.input)
			if got != tt.expected {
				t.Errorf("stripLeadingTitle() = %q, want %q", got, tt.expected)
			}
		})
	}
}
