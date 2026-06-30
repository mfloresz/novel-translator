package store

import (
	"strings"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

func (s *Store) GetAppSettings(userID string) (AppSettings, error) {
	if _, err := s.App.FindRecordById(UsersCollection, userID); err != nil {
		return AppSettings{}, err
	}
	translation, _ := s.getUserTranslationSettings(userID)
	providerSettings, err := s.GetActiveProviderSettings(userID)
	if err != nil {
		return AppSettings{}, err
	}
	aiTimeout := providerSettings.TimeoutMs
	if aiTimeout <= 0 {
		aiTimeout = DefaultAISettings.TimeoutMs
	}
	return AppSettings{
		AI: AISettings{
			Provider:  providerSettings.Provider,
			BaseURL:   providerSettings.BaseURL,
			Model:     providerSettings.Model,
			TimeoutMs: aiTimeout,
		},
		Translation: translation,
	}, nil
}

func (s *Store) GetTheme(userID string) (string, error) {
	user, err := s.App.FindRecordById(UsersCollection, userID)
	if err != nil {
		return "system", err
	}
	return defaultString(user.GetString("theme"), "system"), nil
}

func (s *Store) SaveTheme(userID, theme string) error {
	user, err := s.App.FindRecordById(UsersCollection, userID)
	if err != nil {
		return err
	}
	user.Set("theme", normalizeTheme(theme))
	return s.App.Save(user)
}

func (s *Store) SaveAppSettings(userID string, cfg AppSettings) (AppSettings, error) {
	if err := s.saveUserTranslationSettings(userID, cfg.Translation); err != nil {
		return AppSettings{}, err
	}
	if strings.TrimSpace(cfg.AI.Provider) != "" {
		user, err := s.App.FindRecordById(UsersCollection, userID)
		if err != nil {
			return AppSettings{}, err
		}
		user.Set("active_provider", cfg.AI.Provider)
		if err := s.App.Save(user); err != nil {
			return AppSettings{}, err
		}
		if _, err := s.UpsertProviderSettings(userID, cfg.AI.Provider, cfg.AI.Model, cfg.AI.BaseURL, cfg.AI.TimeoutMs); err != nil {
			return AppSettings{}, err
		}
	}
	return s.GetAppSettings(userID)
}

func (s *Store) GetTranslationDefaults(userID string) (TranslationDefaults, error) {
	return s.getUserTranslationSettings(userID)
}

func (s *Store) getUserTranslationSettings(userID string) (TranslationDefaults, error) {
	cfg := DefaultTranslationDefaults
	record, err := s.App.FindFirstRecordByFilter(UserTranslationCollection, "owner = {:owner}", dbx.Params{"owner": userID})
	if err != nil {
		return cfg, nil
	}
	cfg.AutoSegment = record.GetBool("auto_segment")
	cfg.ThresholdChars = asInt(record.GetFloat("threshold_chars"), cfg.ThresholdChars)
	cfg.MaxChars = asInt(record.GetFloat("max_chars"), cfg.MaxChars)
	cfg.MinChars = asInt(record.GetFloat("min_chars"), cfg.MinChars)
	cfg.MaxRetries = asInt(record.GetFloat("max_retries"), cfg.MaxRetries)
	cfg.EnableCheck = record.GetBool("enable_check")
	cfg.IncludePreviousTitleHints = record.GetBool("include_previous_title_hints")
	cfg.Concurrency = asInt(record.GetFloat("concurrency"), cfg.Concurrency)
	return normalizeTranslation(cfg), nil
}

func (s *Store) saveUserTranslationSettings(userID string, cfg TranslationDefaults) error {
	record, err := s.App.FindFirstRecordByFilter(UserTranslationCollection, "owner = {:owner}", dbx.Params{"owner": userID})
	if err != nil {
		collection, cErr := s.App.FindCollectionByNameOrId(UserTranslationCollection)
		if cErr != nil {
			return cErr
		}
		record = core.NewRecord(collection)
		record.Set("owner", userID)
	}
	cfg = normalizeTranslation(cfg)
	record.Set("auto_segment", cfg.AutoSegment)
	record.Set("threshold_chars", cfg.ThresholdChars)
	record.Set("max_chars", cfg.MaxChars)
	record.Set("min_chars", cfg.MinChars)
	record.Set("max_retries", cfg.MaxRetries)
	record.Set("enable_check", cfg.EnableCheck)
	record.Set("include_previous_title_hints", cfg.IncludePreviousTitleHints)
	record.Set("concurrency", cfg.Concurrency)
	return s.App.Save(record)
}

func (s *Store) GetEffectivePrompts(userID string, novel *Novel) ([]Prompt, error) {
	prompts, err := s.ListPrompts(userID)
	if err != nil {
		return nil, err
	}
	overrides := buildNovelPromptOverrides(novel).ToMap()
	if len(overrides) == 0 {
		return prompts, nil
	}
	for i := range prompts {
		if override, ok := overrides[prompts[i].Key]; ok {
			if value := strings.TrimSpace(override["systemPrompt"]); value != "" {
				prompts[i].SystemPrompt = value
			}
			if value := strings.TrimSpace(override["userPrompt"]); value != "" {
				prompts[i].UserPrompt = value
			}
		}
	}
	return prompts, nil
}
