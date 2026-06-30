package ai

import (
	"context"
)

type Provider interface {
	TranslateTitle(ctx context.Context, input TranslateTitleInput) (string, error)
	TranslateText(ctx context.Context, input TranslateTextInput) (string, error)
	Refine(ctx context.Context, input RefineInput) (RefineOutput, error)
	Check(ctx context.Context, input CheckInput) (CheckOutput, error)
}

type TranslateTitleInput struct {
	SystemPrompt       string            `json:"systemPrompt"`
	TitleOriginal      string            `json:"titleOriginal"`
	PreviousTitleOrig  string            `json:"previousTitleOriginal"`
	PreviousTitleTrans string            `json:"previousTitleTranslated"`
	SourceLanguage     string            `json:"sourceLanguage"`
	TargetLanguage     string            `json:"targetLanguage"`
	Options            map[string]string `json:"options"`
}

type TranslateTextInput struct {
	SystemPrompt    string            `json:"systemPrompt"`
	TextToTranslate string            `json:"textToTranslate"`
	SourceLanguage  string            `json:"sourceLanguage"`
	TargetLanguage  string            `json:"targetLanguage"`
	Options         map[string]string `json:"options"`
}

type RefineInput struct {
	OriginalText   string `json:"originalText"`
	TranslatedText string `json:"translatedText"`
	SourceLanguage string `json:"sourceLanguage"`
	TargetLanguage string `json:"targetLanguage"`
}

type RefineEdit struct {
	Original    string `json:"original"`
	Replacement string `json:"replacement"`
	Reason      string `json:"reason,omitempty"`
}

type RefineOutput struct {
	Edits []RefineEdit `json:"edits"`
}

type CheckInput struct {
	SystemPrompt       string `json:"systemPrompt"`
	TitleOriginal      string `json:"titleOriginal"`
	TitleTranslated    string `json:"titleTranslated"`
	ContentOriginal    string `json:"contentOriginal"`
	ContentTranslated  string `json:"contentTranslated"`
	PreviousTitleOrig  string `json:"previousTitleOriginal"`
	PreviousTitleTrans string `json:"previousTitleTranslated"`
	SourceLanguage     string `json:"sourceLanguage"`
	TargetLanguage     string `json:"targetLanguage"`
}

type CheckOutput struct {
	OK       bool     `json:"ok"`
	Issues   []string `json:"issues"`
	Severity string   `json:"severity"`
}
