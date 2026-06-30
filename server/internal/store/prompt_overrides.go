package store

import (
	"encoding/json"
	"strings"
)

type PromptOverride struct {
	SystemPrompt string `json:"systemPrompt,omitempty"`
	UserPrompt   string `json:"userPrompt,omitempty"`
}

type NovelPromptOverrides struct {
	Translation PromptOverride `json:"translation,omitempty"`
	Refine      PromptOverride `json:"refine,omitempty"`
	Check       PromptOverride `json:"check,omitempty"`
}

func buildNovelPromptOverrides(novel *Novel) NovelPromptOverrides {
	var overrides NovelPromptOverrides
	if novel == nil {
		return overrides
	}

	applyPromptColumns(&overrides.Translation, novel.TranslationSystemPrompt, novel.TranslationUserPrompt)
	applyPromptColumns(&overrides.Refine, novel.RefineSystemPrompt, novel.RefineUserPrompt)
	applyPromptColumns(&overrides.Check, novel.CheckSystemPrompt, novel.CheckUserPrompt)

	return overrides
}

func (o NovelPromptOverrides) ToMap() map[string]map[string]string {
	result := map[string]map[string]string{}
	appendPromptOverride(result, "translation", o.Translation)
	appendPromptOverride(result, "refine", o.Refine)
	appendPromptOverride(result, "check", o.Check)
	return result
}

func BuildNovelPromptOverridesMap(novel *Novel) map[string]map[string]string {
	return buildNovelPromptOverrides(novel).ToMap()
}

func ParseNovelPromptOverrides(value any) NovelPromptOverrides {
	var overrides NovelPromptOverrides
	if value == nil {
		return overrides
	}

	blob, err := json.Marshal(value)
	if err != nil {
		return overrides
	}
	_ = json.Unmarshal(blob, &overrides)
	return overrides
}

func applyPromptColumns(dst *PromptOverride, systemPrompt, userPrompt string) {
	if dst == nil {
		return
	}
	if trimmed := strings.TrimSpace(systemPrompt); trimmed != "" {
		dst.SystemPrompt = systemPrompt
	}
	if trimmed := strings.TrimSpace(userPrompt); trimmed != "" {
		dst.UserPrompt = userPrompt
	}
}

func appendPromptOverride(dst map[string]map[string]string, key string, value PromptOverride) {
	entry := map[string]string{}
	if strings.TrimSpace(value.SystemPrompt) != "" {
		entry["systemPrompt"] = value.SystemPrompt
	}
	if strings.TrimSpace(value.UserPrompt) != "" {
		entry["userPrompt"] = value.UserPrompt
	}
	if len(entry) > 0 {
		dst[key] = entry
	}
}
