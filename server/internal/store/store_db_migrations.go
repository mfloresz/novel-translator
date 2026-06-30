package store

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/pocketbase/pocketbase/core"
)

var legacyNovelFieldNames = []string{"title", "author", "description", "prompts", "source_metadata", "target_metadata"}

func (s *Store) NeedsDatabaseMigration() (bool, error) {
	collection, err := s.App.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		return false, fmt.Errorf("find novels collection: %w", err)
	}
	for _, name := range legacyNovelFieldNames {
		if collection.Fields.GetByName(name) != nil {
			return true, nil
		}
	}

	records, err := s.App.FindRecordsByFilter(NovelsCollection, "", "", 5000, 0)
	if err != nil {
		return false, fmt.Errorf("list novels for migration detection: %w", err)
	}
	for _, record := range records {
		if novelRecordNeedsMigration(record) {
			return true, nil
		}
	}
	return false, nil
}

func (s *Store) RunDatabaseMigrations() error {
	records, err := s.App.FindRecordsByFilter(NovelsCollection, "", "", 5000, 0)
	if err != nil {
		return fmt.Errorf("list novels for migration: %w", err)
	}

	for _, record := range records {
		changed := false

		if record.GetString("source_title") == "" {
			if legacy := strings.TrimSpace(record.GetString("title")); legacy != "" {
				record.Set("source_title", legacy)
				changed = true
			}
		}
		if record.GetString("source_author") == "" {
			if legacy := strings.TrimSpace(record.GetString("author")); legacy != "" {
				record.Set("source_author", legacy)
				changed = true
			}
		}
		if record.GetString("source_description") == "" {
			if legacy := strings.TrimSpace(record.GetString("description")); legacy != "" {
				record.Set("source_description", legacy)
				changed = true
			}
		}

		if raw := strings.TrimSpace(record.GetString("prompts")); raw != "" {
			var overrides NovelPromptOverrides
			if err := json.Unmarshal([]byte(raw), &overrides); err != nil {
				return fmt.Errorf("parse legacy prompts for novel %s: %w", record.Id, err)
			}
			if record.GetString("translation_system_prompt") == "" && overrides.Translation.SystemPrompt != "" {
				record.Set("translation_system_prompt", overrides.Translation.SystemPrompt)
				changed = true
			}
			if record.GetString("translation_user_prompt") == "" && overrides.Translation.UserPrompt != "" {
				record.Set("translation_user_prompt", overrides.Translation.UserPrompt)
				changed = true
			}
			if record.GetString("refine_system_prompt") == "" && overrides.Refine.SystemPrompt != "" {
				record.Set("refine_system_prompt", overrides.Refine.SystemPrompt)
				changed = true
			}
			if record.GetString("refine_user_prompt") == "" && overrides.Refine.UserPrompt != "" {
				record.Set("refine_user_prompt", overrides.Refine.UserPrompt)
				changed = true
			}
			if record.GetString("check_system_prompt") == "" && overrides.Check.SystemPrompt != "" {
				record.Set("check_system_prompt", overrides.Check.SystemPrompt)
				changed = true
			}
			if record.GetString("check_user_prompt") == "" && overrides.Check.UserPrompt != "" {
				record.Set("check_user_prompt", overrides.Check.UserPrompt)
				changed = true
			}
		}

		if changed {
			if err := s.App.Save(record); err != nil {
				return fmt.Errorf("save migrated novel %s: %w", record.Id, err)
			}
		}
	}

	collection, err := s.App.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		return fmt.Errorf("find novels collection: %w", err)
	}

	removed := false
	for _, name := range legacyNovelFieldNames {
		if collection.Fields.GetByName(name) == nil {
			continue
		}
		collection.Fields.RemoveByName(name)
		removed = true
	}
	if removed {
		if err := s.App.Save(collection); err != nil {
			return fmt.Errorf("remove legacy novel fields: %w", err)
		}
	}

	return nil
}

func novelRecordNeedsMigration(record *core.Record) bool {
	if record == nil {
		return false
	}
	if record.GetString("source_title") == "" && strings.TrimSpace(record.GetString("title")) != "" {
		return true
	}
	if record.GetString("source_author") == "" && strings.TrimSpace(record.GetString("author")) != "" {
		return true
	}
	if record.GetString("source_description") == "" && strings.TrimSpace(record.GetString("description")) != "" {
		return true
	}
	if raw := strings.TrimSpace(record.GetString("prompts")); raw != "" {
		var overrides NovelPromptOverrides
		if err := json.Unmarshal([]byte(raw), &overrides); err == nil {
			if record.GetString("translation_system_prompt") == "" && overrides.Translation.SystemPrompt != "" {
				return true
			}
			if record.GetString("translation_user_prompt") == "" && overrides.Translation.UserPrompt != "" {
				return true
			}
			if record.GetString("refine_system_prompt") == "" && overrides.Refine.SystemPrompt != "" {
				return true
			}
			if record.GetString("refine_user_prompt") == "" && overrides.Refine.UserPrompt != "" {
				return true
			}
			if record.GetString("check_system_prompt") == "" && overrides.Check.SystemPrompt != "" {
				return true
			}
			if record.GetString("check_user_prompt") == "" && overrides.Check.UserPrompt != "" {
				return true
			}
		}
	}
	return false
}
