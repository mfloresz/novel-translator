package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"translator-server/internal/ai"
	"translator-server/internal/store"
)

func (s *Server) resolveJobConfig(novel *store.Novel, job *store.Job) (resolvedJobConfig, error) {
	appSettings, err := s.Store.GetAppSettings(job.OwnerID)
	if err != nil {
		return resolvedJobConfig{}, fmt.Errorf("get app settings: %w", err)
	}
	translation, err := s.Store.GetTranslationDefaults(job.OwnerID)
	if err != nil {
		return resolvedJobConfig{}, fmt.Errorf("get translation defaults: %w", err)
	}
	cfg := resolvedJobConfig{Translation: translation}

	providerKey := appSettings.AI.Provider
	modelOverride := appSettings.AI.Model
	if novel != nil && strings.TrimSpace(novel.Glossary) != "" {
		_ = json.Unmarshal([]byte(novel.Glossary), &cfg.Glossary)
	}
	if novel != nil && strings.TrimSpace(novel.AIOptions) != "" {
		var aiOptions novelAIOptions
		if err := json.Unmarshal([]byte(novel.AIOptions), &aiOptions); err == nil {
			if strings.TrimSpace(aiOptions.Provider) != "" {
				providerKey = strings.TrimSpace(aiOptions.Provider)
			}
			if strings.TrimSpace(aiOptions.Model) != "" {
				modelOverride = strings.TrimSpace(aiOptions.Model)
			}
		}
	}
	if strings.TrimSpace(job.Provider) != "" {
		providerKey = strings.TrimSpace(job.Provider)
	}
	if strings.TrimSpace(job.Model) != "" {
		modelOverride = strings.TrimSpace(job.Model)
	}
	cfg.AI, err = s.Store.ResolveProviderAISettings(job.OwnerID, providerKey)
	if err != nil {
		return resolvedJobConfig{}, fmt.Errorf("resolve provider AI settings: %w", err)
	}
	if strings.TrimSpace(modelOverride) != "" {
		cfg.AI.Model = strings.TrimSpace(modelOverride)
		cfg.AI.CustomModel = strings.TrimSpace(modelOverride)
	}
	if novel != nil && strings.TrimSpace(novel.AIOptions) != "" {
		var aiOptions novelAIOptions
		if err := json.Unmarshal([]byte(novel.AIOptions), &aiOptions); err == nil {
			if aiOptions.TimeoutMs > 0 {
				cfg.AI.TimeoutMs = aiOptions.TimeoutMs
			}
		}
	}
	if novel != nil && strings.TrimSpace(novel.TranslationOptions) != "" {
		var tr novelTranslationOptions
		if err := json.Unmarshal([]byte(novel.TranslationOptions), &tr); err == nil {
			if tr.AutoSegment != nil {
				cfg.Translation.AutoSegment = *tr.AutoSegment
			}
			if tr.ThresholdChars > 0 {
				cfg.Translation.ThresholdChars = tr.ThresholdChars
			}
			if tr.MaxChars > 0 {
				cfg.Translation.MaxChars = tr.MaxChars
			}
			if tr.MinChars > 0 {
				cfg.Translation.MinChars = tr.MinChars
			}
			if tr.MaxRetries >= 0 {
				cfg.Translation.MaxRetries = tr.MaxRetries
			}
			if tr.EnableCheck != nil {
				cfg.Translation.EnableCheck = *tr.EnableCheck
			}
			if tr.IncludePreviousTitleHints != nil {
				cfg.Translation.IncludePreviousTitleHints = *tr.IncludePreviousTitleHints
			}
		}
	}
	prompts, err := s.Store.GetEffectivePrompts(job.OwnerID, novel)
	if err != nil {
		return resolvedJobConfig{}, fmt.Errorf("get effective prompts: %w", err)
	}
	applyGlobalPromptFallbacks(&cfg.Prompts, prompts)
	cfg.IncludePrevTitle = cfg.Translation.IncludePreviousTitleHints
	if strings.TrimSpace(cfg.AI.Model) == "" {
		if info, ok := ai.ProviderByID(cfg.AI.Provider); ok {
			cfg.AI.Model = info.DefaultModel
		}
	}
	return cfg, nil
}

func applyGlobalPromptFallbacks(dst *promptSettings, prompts []store.Prompt) {
	for _, p := range prompts {
		tpl := promptTemplate{SystemPrompt: p.SystemPrompt, UserPrompt: p.UserPrompt}
		switch p.Key {
		case "translation":
			if strings.TrimSpace(dst.Translation.SystemPrompt) == "" {
				dst.Translation.SystemPrompt = tpl.SystemPrompt
			}
			if strings.TrimSpace(dst.Translation.UserPrompt) == "" {
				dst.Translation.UserPrompt = tpl.UserPrompt
			}
		case "refine":
			if strings.TrimSpace(dst.Refine.SystemPrompt) == "" {
				dst.Refine.SystemPrompt = tpl.SystemPrompt
			}
			if strings.TrimSpace(dst.Refine.UserPrompt) == "" {
				dst.Refine.UserPrompt = tpl.UserPrompt
			}
		case "check":
			if strings.TrimSpace(dst.Check.SystemPrompt) == "" {
				dst.Check.SystemPrompt = tpl.SystemPrompt
			}
			if strings.TrimSpace(dst.Check.UserPrompt) == "" {
				dst.Check.UserPrompt = tpl.UserPrompt
			}
		}
	}
	if strings.TrimSpace(dst.Translation.SystemPrompt) == "" {
		dst.Translation.SystemPrompt = store.DefaultTranslationSystemPrompt
	}
	if strings.TrimSpace(dst.Translation.UserPrompt) == "" {
		dst.Translation.UserPrompt = store.DefaultTranslationUserPrompt
	}
	if strings.TrimSpace(dst.Refine.SystemPrompt) == "" {
		dst.Refine.SystemPrompt = store.DefaultRefineSystemPrompt
	}
	if strings.TrimSpace(dst.Refine.UserPrompt) == "" {
		dst.Refine.UserPrompt = store.DefaultRefineUserPrompt
	}
	if strings.TrimSpace(dst.Check.SystemPrompt) == "" {
		dst.Check.SystemPrompt = store.DefaultCheckSystemPrompt
	}
	if strings.TrimSpace(dst.Check.UserPrompt) == "" {
		dst.Check.UserPrompt = store.DefaultCheckUserPrompt
	}
}

func (s *Server) newAIProvider(settings store.AISettings) (ai.Provider, error) {
	provider := strings.TrimSpace(settings.Provider)
	if provider == "" {
		provider = store.DefaultAISettings.Provider
	}
	apiKey := strings.TrimSpace(settings.APIKey)
	if apiKey == "" {
		return nil, errors.New("AI API key not configured in database")
	}
	model := effectiveModel(settings)
	timeout := time.Duration(settings.TimeoutMs) * time.Millisecond
	baseURL := strings.TrimSpace(settings.BaseURL)
	if baseURL == "" {
		baseURL = store.DefaultAISettings.BaseURL
	}
	if info, ok := ai.ProviderByID(provider); ok {
		if baseURL == "" {
			baseURL = info.BaseURL
		}
		return &ai.OpenAIProvider{APIKey: apiKey, BaseURL: baseURL, Model: model, Timeout: timeout, ProviderOptions: info.GoAIOptions}, nil
	}
	return &ai.OpenAIProvider{APIKey: apiKey, BaseURL: baseURL, Model: model, Timeout: timeout}, nil
}

func effectiveModel(settings store.AISettings) string {
	if strings.TrimSpace(settings.Model) != "" {
		return settings.Model
	}
	if info, ok := ai.ProviderByID(settings.Provider); ok {
		return info.DefaultModel
	}
	return ""
}
