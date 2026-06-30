package api

import "translator-server/internal/store"

type promptTemplate struct {
	SystemPrompt string `json:"systemPrompt"`
	UserPrompt   string `json:"userPrompt"`
}

type promptSettings struct {
	Translation promptTemplate `json:"translation"`
	Refine      promptTemplate `json:"refine"`
	Check       promptTemplate `json:"check"`
}

type glossaryEntry struct {
	Source  string `json:"source"`
	Target  string `json:"target"`
	Context string `json:"context,omitempty"`
}

type novelAIOptions struct {
	Provider  string `json:"provider"`
	Model     string `json:"model"`
	TimeoutMs int    `json:"timeoutMs"`
}

type novelTranslationOptions struct {
	AutoSegment               *bool `json:"autoSegment,omitempty"`
	ThresholdChars            int   `json:"thresholdChars,omitempty"`
	MaxChars                  int   `json:"maxChars,omitempty"`
	MinChars                  int   `json:"minChars,omitempty"`
	MaxRetries                int   `json:"maxRetries,omitempty"`
	EnableCheck               *bool `json:"enableCheck,omitempty"`
	IncludePreviousTitleHints *bool `json:"includePreviousChapterTitles,omitempty"`
}

type resolvedJobConfig struct {
	AI               store.AISettings
	Translation      store.TranslationDefaults
	Glossary         []glossaryEntry
	Prompts          promptSettings
	IncludePrevTitle bool
}

type chapterSegment struct {
	Index     int
	Text      string
	StartChar int
	EndChar   int
}

type chapterSegmentationStatus struct {
	Applied      bool
	SegmentCount int
}

type refineChunk struct {
	Index              int
	StartLine          int
	EndLine            int
	OriginalContext    string
	OriginalChunk      string
	TranslationContext string
	TranslationChunk   string
}
