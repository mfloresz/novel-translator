package ai

import (
	"strings"
	"testing"
)

func TestBuildTranslationTitlePrompt_SendsOnlyStructuredTitle(t *testing.T) {
	prompt := buildTranslationTitlePrompt(TranslateTitleInput{
		TitleOriginal:  "Chapter Seven",
		SourceLanguage: "English",
		TargetLanguage: "Spanish",
	})

	expected := `{"title_original":"Chapter Seven"}`
	if prompt != expected {
		t.Fatalf("unexpected prompt:\nwant: %s\ngot:  %s", expected, prompt)
	}
}

func TestBuildTranslationTitlePrompt_OmitsPreviousTitleWhenEmpty(t *testing.T) {
	prompt := buildTranslationTitlePrompt(TranslateTitleInput{
		TitleOriginal:      "Chapter Seven",
		PreviousTitleOrig:  "   ",
		PreviousTitleTrans: "",
	})

	expected := `{"title_original":"Chapter Seven"}`
	if prompt != expected {
		t.Fatalf("unexpected prompt:\nwant: %s\ngot:  %s", expected, prompt)
	}
}

func TestBuildTranslationTitlePrompt_DropsPreviousTitleWhenToggleDisabled(t *testing.T) {
	for _, title := range []string{"Chapter 1", "Chapter 2", "Chapter 12", "Chapter 1000"} {
		t.Run(title, func(t *testing.T) {
			prompt := buildTranslationTitlePrompt(TranslateTitleInput{
				TitleOriginal:      title,
				PreviousTitleOrig:  "",
				PreviousTitleTrans: "",
			})
			expected := `{"title_original":"` + title + `"}`
			if prompt != expected {
				t.Fatalf("toggle off leaked previous title fields\nwant: %s\ngot:  %s", expected, prompt)
			}
		})
	}
}

func TestBuildTranslationTitlePrompt_IncludesPreviousTitleWhenSet(t *testing.T) {
	prompt := buildTranslationTitlePrompt(TranslateTitleInput{
		TitleOriginal:      "Chapter Seven",
		PreviousTitleOrig:  "Chapter Six",
		PreviousTitleTrans: "Capítulo Seis",
		SourceLanguage:     "English",
		TargetLanguage:     "Spanish",
	})

	expected := `{"title_original":"Chapter Seven","previous_title_original":"Chapter Six","previous_title_translated":"Capítulo Seis"}`
	if prompt != expected {
		t.Fatalf("unexpected prompt:\nwant: %s\ngot:  %s", expected, prompt)
	}
}

func TestBuildTranslationTitleSystemPrompt_AppendsSchemaHint(t *testing.T) {
	got := buildTranslationTitleSystemPrompt(TranslateTitleInput{SystemPrompt: "Translate faithfully."})
	if !strings.Contains(got, "Translate faithfully.") {
		t.Fatalf("system prompt missing user base:\n%s", got)
	}
	if !strings.Contains(got, "title_original") {
		t.Fatal("system prompt must mention title_original field semantics")
	}
	if !strings.Contains(got, `{"title_translated": "..."}`) {
		t.Fatal("system prompt must require title_translated-only structured output")
	}
	if !strings.Contains(got, "structured output schema") {
		t.Fatal("system prompt must reference the structured output schema")
	}
}

func TestBuildTranslationContentPrompt_SendsPlainTextOnly(t *testing.T) {
	prompt := buildTranslationContentPrompt(TranslateTextInput{
		TextToTranslate: "Body text",
	})
	if prompt != "Body text" {
		t.Fatalf("unexpected plain-text prompt: %q", prompt)
	}
}

func TestBuildTranslationContentSystemPrompt_ExplainsPlainTextResponse(t *testing.T) {
	got := buildTranslationContentSystemPrompt(TranslateTextInput{SystemPrompt: "Translate faithfully."})
	if !strings.Contains(got, "Translate faithfully.") {
		t.Fatalf("system prompt missing user base:\n%s", got)
	}
	if !strings.Contains(got, "plain text") {
		t.Fatal("system prompt must explain that the user message is plain text")
	}
	if !strings.Contains(got, "Return only the translated text.") {
		t.Fatal("system prompt must require plain translated text output")
	}
	if strings.Contains(got, "structured output schema") {
		t.Fatal("content system prompt must not require structured output")
	}
}

func TestBuildTranslationContentSystemPrompt_HandlesEmptyBase(t *testing.T) {
	got := buildTranslationContentSystemPrompt(TranslateTextInput{SystemPrompt: "   "})
	if !strings.Contains(got, "plain text") {
		t.Fatal("content system prompt must still explain plain-text input when base is empty")
	}
	if !strings.Contains(got, "Do not return JSON") {
		t.Fatal("content system prompt must forbid JSON output when base is empty")
	}
}
