package ai

import (
	"encoding/json"
	"strings"
)

type translationTitlePromptPayload struct {
	TitleOriginal           string `json:"title_original"`
	PreviousTitleOriginal   string `json:"previous_title_original,omitempty"`
	PreviousTitleTranslated string `json:"previous_title_translated,omitempty"`
}

func buildTranslationTitlePrompt(in TranslateTitleInput) string {
	payload := translationTitlePromptPayload{
		TitleOriginal:           strings.TrimSpace(in.TitleOriginal),
		PreviousTitleOriginal:   strings.TrimSpace(in.PreviousTitleOrig),
		PreviousTitleTranslated: strings.TrimSpace(in.PreviousTitleTrans),
	}
	b, _ := json.Marshal(payload)
	return string(b)
}

func buildTranslationTitleSystemPrompt(in TranslateTitleInput) string {
	instructions := []string{}
	if trimmed := strings.TrimSpace(in.SystemPrompt); trimmed != "" {
		instructions = append(instructions, trimmed)
	}
	instructions = append(instructions,
		"The user message is a JSON object with structured fields.",
		"Read title_original as the chapter title to translate.",
		"Use previous_title_original and previous_title_translated as context for consistency with the previous chapter's title translation.",
		"Return only the translated title in structured output.",
		"Respond with valid JSON matching this format:",
		`{"title_translated": "..."}`,
		"Return the translated data matching the required structured output schema.",
	)
	return strings.Join(instructions, "\n\n")
}

func buildTranslationContentPrompt(in TranslateTextInput) string {
	return strings.TrimSpace(in.TextToTranslate)
}

func buildTranslationContentSystemPrompt(in TranslateTextInput) string {
	instructions := []string{}
	if trimmed := strings.TrimSpace(in.SystemPrompt); trimmed != "" {
		instructions = append(instructions, trimmed)
	}
	instructions = append(instructions,
		"The user message contains only the chapter body or current segment as plain text.",
		"Translate only that content.",
		"Return only the translated text.",
		"Do not return JSON, labels, markdown, notes, or commentary.",
	)
	return strings.Join(instructions, "\n\n")
}
