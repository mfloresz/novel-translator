package store

import "testing"

func TestBuildNovelPromptOverridesMapUsesOnlyColumnOverrides(t *testing.T) {
	novel := &Novel{
		TranslationSystemPrompt: "new translation",
		TranslationUserPrompt:   "new translation user",
		CheckUserPrompt:         "new check user",
	}

	overrides := BuildNovelPromptOverridesMap(novel)

	if got := overrides["translation"]["systemPrompt"]; got != "new translation" {
		t.Fatalf("translation system prompt = %q, want %q", got, "new translation")
	}
	if got := overrides["translation"]["userPrompt"]; got != "new translation user" {
		t.Fatalf("translation user prompt = %q, want %q", got, "new translation user")
	}
	if _, ok := overrides["refine"]; ok {
		t.Fatal("did not expect refine override when all refine columns are empty")
	}
	if got := overrides["check"]["userPrompt"]; got != "new check user" {
		t.Fatalf("check user prompt = %q, want %q", got, "new check user")
	}
}

func TestParseNovelPromptOverrides(t *testing.T) {
	input := map[string]any{
		"translation": map[string]any{
			"systemPrompt": "sys",
			"userPrompt":   "usr",
		},
	}

	overrides := ParseNovelPromptOverrides(input)

	if overrides.Translation.SystemPrompt != "sys" {
		t.Fatalf("translation system prompt = %q, want %q", overrides.Translation.SystemPrompt, "sys")
	}
	if overrides.Translation.UserPrompt != "usr" {
		t.Fatalf("translation user prompt = %q, want %q", overrides.Translation.UserPrompt, "usr")
	}
}
