package store

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

func (s *Store) GetActiveProviderSettings(userID string) (ProviderSetting, error) {
	user, err := s.App.FindRecordById(UsersCollection, userID)
	if err != nil {
		return ProviderSetting{}, err
	}
	activeProvider := defaultString(user.GetString("active_provider"), DefaultAISettings.Provider)
	providers, err := s.ListProviderSettings(userID)
	if err != nil {
		return ProviderSetting{}, err
	}
	for _, item := range providers {
		if item.Provider == activeProvider {
			return item, nil
		}
	}
	if len(providers) == 0 {
		return ProviderSetting{}, fmt.Errorf("no providers available")
	}
	return providers[0], nil
}

func (s *Store) ListProviderSettings(userID string) ([]ProviderSetting, error) {
	providers, err := s.App.FindRecordsByFilter(ProvidersCollection, "enabled = true", "key", 200, 0)
	if err != nil {
		return nil, err
	}
	settings, err := s.App.FindRecordsByFilter(UserProviderSettingsCollection, "owner = {:owner}", "", 200, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	byProviderID := map[string]*core.Record{}
	for _, item := range settings {
		byProviderID[item.GetString("provider")] = item
	}
	out := make([]ProviderSetting, 0, len(providers))
	for _, provider := range providers {
		item := ProviderSetting{
			Provider: provider.GetString("key"),
			Label:    provider.GetString("label"),
			BaseURL:  provider.GetString("base_url"),
			Model:    provider.GetString("default_model"),
			Kind:     provider.GetString("kind"),
			Enabled:  provider.GetBool("enabled"),
		}
		if raw := provider.GetString("models_json"); raw != "" {
			_ = json.Unmarshal([]byte(raw), &item.Models)
		}
		if setting := byProviderID[provider.Id]; setting != nil {
			if model := strings.TrimSpace(setting.GetString("model")); model != "" {
				item.Model = model
			}
			if baseURL := strings.TrimSpace(setting.GetString("base_url")); baseURL != "" {
				item.BaseURL = baseURL
			}
			item.APIKeyConfigured = setting.GetBool("api_key_configured")
			item.APIKeyUpdatedAt = setting.GetString("api_key_updated_at")
			item.TimeoutMs = setting.GetInt("timeout_ms")
		}
		out = append(out, item)
	}
	return out, nil
}

func (s *Store) UpsertProviderSettings(userID, providerKey, model, baseURL string, timeoutMs ...int) (ProviderSetting, error) {
	providerRecord, err := s.getProviderByKey(providerKey)
	if err != nil {
		return ProviderSetting{}, err
	}
	record, err := s.findUserProviderSettingsRecord(userID, providerRecord.Id)
	if err != nil {
		collection, cErr := s.App.FindCollectionByNameOrId(UserProviderSettingsCollection)
		if cErr != nil {
			return ProviderSetting{}, cErr
		}
		record = core.NewRecord(collection)
		record.Set("owner", userID)
		record.Set("provider", providerRecord.Id)
	}
	record.Set("model", strings.TrimSpace(model))
	record.Set("base_url", strings.TrimSpace(baseURL))
	if len(timeoutMs) > 0 && timeoutMs[0] > 0 {
		record.Set("timeout_ms", timeoutMs[0])
	} else {
		record.Set("timeout_ms", nil)
	}
	if err := s.App.Save(record); err != nil {
		return ProviderSetting{}, err
	}
	list, err := s.ListProviderSettings(userID)
	if err != nil {
		return ProviderSetting{}, err
	}
	for _, item := range list {
		if item.Provider == providerKey {
			return item, nil
		}
	}
	return ProviderSetting{}, fmt.Errorf("provider settings not found after update")
}

func (s *Store) ReplaceProviderAPIKey(userID, providerKey, apiKey string) (ProviderSetting, error) {
	providerRecord, err := s.getProviderByKey(providerKey)
	if err != nil {
		return ProviderSetting{}, err
	}
	record, err := s.findUserProviderSettingsRecord(userID, providerRecord.Id)
	if err != nil {
		collection, cErr := s.App.FindCollectionByNameOrId(UserProviderSettingsCollection)
		if cErr != nil {
			return ProviderSetting{}, cErr
		}
		record = core.NewRecord(collection)
		record.Set("owner", userID)
		record.Set("provider", providerRecord.Id)
	}
	encrypted, err := s.Encryptor.Encrypt(strings.TrimSpace(apiKey))
	if err != nil {
		return ProviderSetting{}, err
	}
	record.Set("api_key_encrypted", encrypted)
	record.Set("api_key_configured", strings.TrimSpace(apiKey) != "")
	record.Set("api_key_updated_at", time.Now().UTC().Format(time.RFC3339))
	if err := s.App.Save(record); err != nil {
		return ProviderSetting{}, err
	}
	return s.UpsertProviderSettings(userID, providerKey, record.GetString("model"), record.GetString("base_url"))
}

func (s *Store) DeleteProviderAPIKey(userID, providerKey string) error {
	providerRecord, err := s.getProviderByKey(providerKey)
	if err != nil {
		return err
	}
	record, err := s.findUserProviderSettingsRecord(userID, providerRecord.Id)
	if err != nil {
		return nil
	}
	record.Set("api_key_encrypted", "")
	record.Set("api_key_configured", false)
	record.Set("api_key_updated_at", "")
	return s.App.Save(record)
}

func (s *Store) ResolveProviderAISettings(userID, providerKey string) (AISettings, error) {
	providers, err := s.ListProviderSettings(userID)
	if err != nil {
		return AISettings{}, err
	}
	for _, item := range providers {
		if item.Provider != providerKey {
			continue
		}
		providerRecord, err := s.getProviderByKey(providerKey)
		if err != nil {
			return AISettings{}, err
		}
		settingsRecord, _ := s.findUserProviderSettingsRecord(userID, providerRecord.Id)
		apiKey := ""
		if settingsRecord != nil {
			apiKey, err = s.Encryptor.Decrypt(settingsRecord.GetString("api_key_encrypted"))
			if err != nil {
				return AISettings{}, err
			}
		}
		timeoutMs := item.TimeoutMs
		if timeoutMs <= 0 {
			timeoutMs = DefaultAISettings.TimeoutMs
		}
		concurrency := item.Concurrency
		if concurrency <= 0 {
			concurrency = DefaultAISettings.Concurrency
		}
		return AISettings{
			Provider:    providerKey,
			APIKey:      apiKey,
			BaseURL:     item.BaseURL,
			Model:       item.Model,
			TimeoutMs:   timeoutMs,
			Concurrency: concurrency,
		}, nil
	}
	return AISettings{}, fmt.Errorf("provider %s not found", providerKey)
}

func (s *Store) getProviderByKey(providerKey string) (*core.Record, error) {
	return s.App.FindFirstRecordByFilter(ProvidersCollection, "key = {:key}", dbx.Params{"key": providerKey})
}

func (s *Store) findUserProviderSettingsRecord(userID, providerID string) (*core.Record, error) {
	return s.App.FindFirstRecordByFilter(UserProviderSettingsCollection, "owner = {:owner} && provider = {:provider}", dbx.Params{"owner": userID, "provider": providerID})
}
