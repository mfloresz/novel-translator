package store

import (
	"errors"
	"fmt"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"translator-server/internal/secure"
)

const (
	UsersCollection                = "users"
	ProvidersCollection            = "providers"
	UserProviderSettingsCollection = "user_provider_settings"
	UserPromptSettingsCollection   = "user_prompt_settings"
	UserTranslationCollection      = "user_translation_settings"
	NovelsCollection               = "novels"
	ChaptersCollection             = "chapters"
	JobsCollection                 = "translation_jobs"
	EpubsCollection                = "epubs"
	ReadingProgressCollection      = "reading_progress"
)

var ErrNotFound = errors.New("not found")
var ErrForbidden = errors.New("forbidden")

type Store struct {
	App       core.App
	Encryptor *secure.Encryptor
}

func New(app core.App, encryptor *secure.Encryptor) *Store {
	return &Store{App: app, Encryptor: encryptor}
}

func (s *Store) EnsureSchema() error {
	users, err := s.ensureUsersCollection()
	if err != nil {
		return err
	}
	providers, err := s.ensureProvidersCollection(users)
	if err != nil {
		return err
	}
	if _, err := s.ensureUserProviderSettingsCollection(users, providers); err != nil {
		return err
	}
	if _, err := s.ensureUserPromptSettingsCollection(users); err != nil {
		return err
	}
	if _, err := s.ensureUserTranslationSettingsCollection(users); err != nil {
		return err
	}
	novels, err := s.ensureNovelsCollection(users)
	if err != nil {
		return err
	}
	chapters, err := s.ensureChaptersCollection(novels)
	if err != nil {
		return err
	}
	if err := s.migrateChapterCascadeDelete(chapters); err != nil {
		return err
	}
	jobs, err := s.ensureJobsCollection(users, novels)
	if err != nil {
		return err
	}
	if err := s.migrateJobCascadeDelete(jobs); err != nil {
		return err
	}
	epubs, err := s.ensureEpubsCollection(novels)
	if err != nil {
		return err
	}
	if err := s.migrateEpubCascadeDelete(epubs); err != nil {
		return err
	}
	if _, err := s.ensureReadingProgressCollection(users, novels); err != nil {
		return err
	}
	if err := s.seedProviders(); err != nil {
		return err
	}
	if err := s.BackfillChapterCharCounts(); err != nil {
		return err
	}
	if err := s.BackfillNovelStats(); err != nil {
		return err
	}
	return nil
}

func (s *Store) ListPrompts(userID string) ([]Prompt, error) {
	defaults := []Prompt{
		{Key: "translation", Label: "Traducción", Description: "Prompt global para traducción de capítulos.", SystemPrompt: DefaultTranslationSystemPrompt, UserPrompt: DefaultTranslationUserPrompt, Active: 1},
		{Key: "refine", Label: "Refinamiento", Description: "Prompt global para mejorar traducciones generadas.", SystemPrompt: DefaultRefineSystemPrompt, UserPrompt: DefaultRefineUserPrompt, Active: 1},
		{Key: "check", Label: "Verificación", Description: "Prompt global para revisar calidad de traducción.", SystemPrompt: DefaultCheckSystemPrompt, UserPrompt: DefaultCheckUserPrompt, Active: 1},
	}
	records, err := s.App.FindRecordsByFilter(UserPromptSettingsCollection, "owner = {:owner}", "", 20, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	byKey := map[string]*core.Record{}
	for _, record := range records {
		byKey[record.GetString("key")] = record
	}
	out := make([]Prompt, 0, len(defaults))
	for _, item := range defaults {
		if record := byKey[item.Key]; record != nil {
			item.Label = defaultString(record.GetString("label"), item.Label)
			item.Description = defaultString(record.GetString("description"), item.Description)
			item.SystemPrompt = defaultString(record.GetString("system_prompt"), item.SystemPrompt)
			item.UserPrompt = defaultString(record.GetString("user_prompt"), item.UserPrompt)
			if !record.GetBool("active") {
				item.Active = 0
			}
			item.UpdatedAt = record.GetString("updated")
		}
		out = append(out, item)
	}
	return out, nil
}

func (s *Store) UpsertPrompt(userID string, prompt Prompt) (Prompt, error) {
	record, err := s.App.FindFirstRecordByFilter(UserPromptSettingsCollection, "owner = {:owner} && key = {:key}", dbx.Params{"owner": userID, "key": prompt.Key})
	if err != nil {
		collection, cErr := s.App.FindCollectionByNameOrId(UserPromptSettingsCollection)
		if cErr != nil {
			return Prompt{}, cErr
		}
		record = core.NewRecord(collection)
		record.Set("owner", userID)
		record.Set("key", prompt.Key)
	}
	record.Set("label", prompt.Label)
	record.Set("description", prompt.Description)
	record.Set("system_prompt", prompt.SystemPrompt)
	record.Set("user_prompt", prompt.UserPrompt)
	record.Set("active", prompt.Active != 0)
	if err := s.App.Save(record); err != nil {
		return Prompt{}, err
	}
	list, err := s.ListPrompts(userID)
	if err != nil {
		return Prompt{}, err
	}
	for _, item := range list {
		if item.Key == prompt.Key {
			return item, nil
		}
	}
	return Prompt{}, fmt.Errorf("prompt not found after update")
}
