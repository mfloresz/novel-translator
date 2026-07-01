package store

import (
	"encoding/json"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/types"
	"translator-server/internal/ai"
)

func addSystemDateFields(c *core.Collection) {
	if c.Fields.GetByName("created") == nil {
		c.Fields.Add(&core.AutodateField{Name: "created", OnCreate: true})
	}
	if c.Fields.GetByName("updated") == nil {
		c.Fields.Add(&core.AutodateField{Name: "updated", OnCreate: true, OnUpdate: true})
	}
}

func (s *Store) migrateSystemDateFields(c *core.Collection) (*core.Collection, error) {
	if c.Fields.GetByName("created") != nil && c.Fields.GetByName("updated") != nil {
		return c, nil
	}
	addSystemDateFields(c)
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func enableNovelCascadeDelete(c *core.Collection) (bool, error) {
	rel, ok := c.Fields.GetByName("novel").(*core.RelationField)
	if !ok || rel == nil || rel.CascadeDelete {
		return false, nil
	}
	rel.CascadeDelete = true
	c.Fields.Add(rel)
	return true, nil
}

func (s *Store) ensureField(collection *core.Collection, field core.Field) error {
	if existing := collection.Fields.GetByName(field.GetName()); existing != nil {
		return nil
	}
	collection.Fields.Add(field)
	return s.App.Save(collection)
}

func (s *Store) migrateChapterCascadeDelete(c *core.Collection) error {
	changed, err := enableNovelCascadeDelete(c)
	if err != nil {
		return err
	}
	if !changed {
		return nil
	}
	return s.App.Save(c)
}

func (s *Store) migrateJobCascadeDelete(c *core.Collection) error {
	changed, err := enableNovelCascadeDelete(c)
	if err != nil {
		return err
	}
	if !changed {
		return nil
	}
	return s.App.Save(c)
}

func (s *Store) migrateEpubCascadeDelete(c *core.Collection) error {
	changed, err := enableNovelCascadeDelete(c)
	if err != nil {
		return err
	}
	if !changed {
		return nil
	}
	return s.App.Save(c)
}

func (s *Store) ensureUsersCollection() (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(UsersCollection); err == nil {
		return s.migrateUsersCollection(existing)
	}
	c := core.NewAuthCollection(UsersCollection)
	c.ListRule = types.Pointer("@request.auth.id != '' && @request.auth.id = id")
	c.ViewRule = types.Pointer("@request.auth.id != '' && @request.auth.id = id")
	c.UpdateRule = types.Pointer("@request.auth.id != '' && @request.auth.id = id")
	c.DeleteRule = nil
	c.CreateRule = nil
	c.Fields.Add(&core.TextField{Name: "name", Max: 120})
	c.Fields.Add(&core.SelectField{Name: "theme", Values: []string{"light", "dark", "system"}, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "active_provider", Max: 120})
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) migrateUsersCollection(c *core.Collection) (*core.Collection, error) {
	if err := s.ensureField(c, &core.TextField{Name: "name", Max: 120}); err != nil {
		return nil, err
	}
	if err := s.ensureField(c, &core.SelectField{Name: "theme", Values: []string{"light", "dark", "system"}, MaxSelect: 1}); err != nil {
		return nil, err
	}
	if err := s.ensureField(c, &core.TextField{Name: "active_provider", Max: 120}); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureProvidersCollection(users *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(ProvidersCollection); err == nil {
		return existing, nil
	}
	c := core.NewBaseCollection(ProvidersCollection)
	c.ListRule = types.Pointer("@request.auth.id != ''")
	c.ViewRule = types.Pointer("@request.auth.id != ''")
	c.CreateRule = nil
	c.UpdateRule = nil
	c.DeleteRule = nil
	c.Fields.Add(&core.TextField{Name: "key", Required: true, Max: 120})
	c.Fields.Add(&core.TextField{Name: "label", Required: true, Max: 120})
	c.Fields.Add(&core.TextField{Name: "base_url", Required: true, Max: 500})
	c.Fields.Add(&core.TextField{Name: "default_model", Required: true, Max: 200})
	c.Fields.Add(&core.TextField{Name: "kind", Required: true, Max: 80})
	c.Fields.Add(&core.TextField{Name: "models_json"})
	c.Fields.Add(&core.BoolField{Name: "enabled"})
	c.Fields.Add(&core.RelationField{Name: "owner", CollectionId: users.Id, MaxSelect: 1})
	c.AddIndex("idx_providers_key_unique", true, "key", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureUserProviderSettingsCollection(users, providers *core.Collection) (*core.Collection, error) {
	existing, err := s.App.FindCollectionByNameOrId(UserProviderSettingsCollection)
	if err == nil {
		if err := s.ensureField(existing, &core.NumberField{Name: "timeout_ms"}); err != nil {
			return nil, err
		}
		return existing, nil
	}
	c := core.NewBaseCollection(UserProviderSettingsCollection)
	ownerOnly := "@request.auth.id != '' && owner = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "owner", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.RelationField{Name: "provider", Required: true, CollectionId: providers.Id, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "model", Max: 200})
	c.Fields.Add(&core.TextField{Name: "base_url", Max: 500})
	c.Fields.Add(&core.TextField{Name: "api_key_encrypted"})
	c.Fields.Add(&core.BoolField{Name: "api_key_configured"})
	c.Fields.Add(&core.DateField{Name: "api_key_updated_at"})
	c.Fields.Add(&core.NumberField{Name: "timeout_ms"})
	c.AddIndex("idx_user_provider_unique", true, "owner,provider", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureUserPromptSettingsCollection(users *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(UserPromptSettingsCollection); err == nil {
		return existing, nil
	}
	c := core.NewBaseCollection(UserPromptSettingsCollection)
	ownerOnly := "@request.auth.id != '' && owner = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "owner", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "key", Required: true, Max: 64})
	c.Fields.Add(&core.TextField{Name: "label", Max: 120})
	c.Fields.Add(&core.TextField{Name: "description"})
	c.Fields.Add(&core.EditorField{Name: "system_prompt"})
	c.Fields.Add(&core.EditorField{Name: "user_prompt"})
	c.Fields.Add(&core.BoolField{Name: "active"})
	c.AddIndex("idx_user_prompt_unique", true, "owner,key", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureUserTranslationSettingsCollection(users *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(UserTranslationCollection); err == nil {
		return existing, nil
	}
	c := core.NewBaseCollection(UserTranslationCollection)
	ownerOnly := "@request.auth.id != '' && owner = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "owner", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.BoolField{Name: "auto_segment"})
	c.Fields.Add(&core.NumberField{Name: "threshold_chars"})
	c.Fields.Add(&core.NumberField{Name: "max_chars"})
	c.Fields.Add(&core.NumberField{Name: "min_chars"})
	c.Fields.Add(&core.NumberField{Name: "max_retries"})
	c.Fields.Add(&core.BoolField{Name: "enable_check"})
	c.Fields.Add(&core.BoolField{Name: "include_previous_title_hints"})
	c.Fields.Add(&core.NumberField{Name: "concurrency"})
	c.AddIndex("idx_user_translation_owner_unique", true, "owner", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureNovelsCollection(users *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(NovelsCollection); err == nil {
		return s.migrateNovelsCollection(existing)
	}
	c := core.NewBaseCollection(NovelsCollection)
	c.ListRule = types.Pointer("@request.auth.id != '' && (owner = @request.auth.id || is_public = true)")
	c.ViewRule = types.Pointer("@request.auth.id != '' && (owner = @request.auth.id || is_public = true)")
	c.CreateRule = types.Pointer("@request.auth.id != '' && owner = @request.auth.id")
	c.UpdateRule = types.Pointer("@request.auth.id != '' && owner = @request.auth.id")
	c.DeleteRule = types.Pointer("@request.auth.id != '' && owner = @request.auth.id")
	c.Fields.Add(&core.RelationField{Name: "owner", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "source_language", Required: true, Max: 32})
	c.Fields.Add(&core.TextField{Name: "target_language", Required: true, Max: 32})
	c.Fields.Add(&core.TextField{Name: "source_title", Required: true, Max: 250})
	c.Fields.Add(&core.TextField{Name: "source_author", Max: 250})
	c.Fields.Add(&core.EditorField{Name: "source_description"})
	c.Fields.Add(&core.TextField{Name: "source_series", Max: 250})
	c.Fields.Add(&core.TextField{Name: "source_number", Max: 64})
	c.Fields.Add(&core.TextField{Name: "target_title", Max: 250})
	c.Fields.Add(&core.TextField{Name: "target_author", Max: 250})
	c.Fields.Add(&core.EditorField{Name: "target_description"})
	c.Fields.Add(&core.TextField{Name: "target_series", Max: 250})
	c.Fields.Add(&core.TextField{Name: "target_number", Max: 64})
	c.Fields.Add(&core.TextField{Name: "glossary"})
	c.Fields.Add(&core.EditorField{Name: "translation_system_prompt"})
	c.Fields.Add(&core.EditorField{Name: "translation_user_prompt"})
	c.Fields.Add(&core.EditorField{Name: "refine_system_prompt"})
	c.Fields.Add(&core.EditorField{Name: "refine_user_prompt"})
	c.Fields.Add(&core.EditorField{Name: "check_system_prompt"})
	c.Fields.Add(&core.EditorField{Name: "check_user_prompt"})
	c.Fields.Add(&core.EditorField{Name: "notes"})
	c.Fields.Add(&core.TextField{Name: "ai_options"})
	c.Fields.Add(&core.TextField{Name: "translation_options"})
	c.Fields.Add(&core.TextField{Name: "cleanup_rules"})
	c.Fields.Add(&core.TextField{Name: "url", Max: 1000})
	c.Fields.Add(&core.EditorField{Name: "custom_commands"})
	c.Fields.Add(&core.SelectField{Name: "status", Values: []string{"ongoing", "completed", "hiatus", "cancelled"}, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "tags"})
	c.Fields.Add(&core.FileField{Name: "cover", MaxSelect: 1})
	c.Fields.Add(&core.BoolField{Name: "is_public"})
	c.Fields.Add(&core.NumberField{Name: "chapter_count"})
	c.Fields.Add(&core.NumberField{Name: "translated_count"})
	c.Fields.Add(&core.NumberField{Name: "completed_count"})
	c.Fields.Add(&core.NumberField{Name: "original_char_count"})
	c.Fields.Add(&core.NumberField{Name: "translated_char_count"})
	c.Fields.Add(&core.NumberField{Name: "refined_char_count"})
	c.Fields.Add(&core.NumberField{Name: "total_char_count"})
	c.Fields.Add(&core.NumberField{Name: "max_chapter_order"})
	addSystemDateFields(c)
	c.AddIndex("idx_novels_owner", false, "owner", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) migrateNovelsCollection(c *core.Collection) (*core.Collection, error) {
	c, err := s.migrateSystemDateFields(c)
	if err != nil {
		return nil, err
	}
	for _, f := range []core.Field{
		&core.TextField{Name: "source_title", Max: 250},
		&core.TextField{Name: "source_author", Max: 250},
		&core.EditorField{Name: "source_description"},
		&core.TextField{Name: "source_series", Max: 250},
		&core.TextField{Name: "source_number", Max: 64},
		&core.TextField{Name: "target_title", Max: 250},
		&core.TextField{Name: "target_author", Max: 250},
		&core.EditorField{Name: "target_description"},
		&core.TextField{Name: "target_series", Max: 250},
		&core.TextField{Name: "target_number", Max: 64},
		&core.NumberField{Name: "chapter_count"},
		&core.NumberField{Name: "translated_count"},
		&core.NumberField{Name: "completed_count"},
		&core.NumberField{Name: "original_char_count"},
		&core.NumberField{Name: "translated_char_count"},
		&core.NumberField{Name: "refined_char_count"},
		&core.NumberField{Name: "total_char_count"},
		&core.NumberField{Name: "max_chapter_order"},
		&core.EditorField{Name: "translation_system_prompt"},
		&core.EditorField{Name: "translation_user_prompt"},
		&core.EditorField{Name: "refine_system_prompt"},
		&core.EditorField{Name: "refine_user_prompt"},
		&core.EditorField{Name: "check_system_prompt"},
		&core.EditorField{Name: "check_user_prompt"},
		&core.SelectField{Name: "status", Values: []string{"ongoing", "completed", "hiatus", "cancelled"}, MaxSelect: 1},
		&core.TextField{Name: "tags"},
	} {
		if err := s.ensureField(c, f); err != nil {
			return nil, err
		}
	}
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureChaptersCollection(novels *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(ChaptersCollection); err == nil {
		c, err := s.migrateSystemDateFields(existing)
		if err != nil {
			return nil, err
		}
		for _, field := range []core.Field{
			&core.NumberField{Name: "original_char_count"},
			&core.NumberField{Name: "translated_char_count"},
			&core.NumberField{Name: "refined_char_count"},
		} {
			if err := s.ensureField(c, field); err != nil {
				return nil, err
			}
		}
		return c, nil
	}
	c := core.NewBaseCollection(ChaptersCollection)
	visible := "@request.auth.id != '' && (novel.owner = @request.auth.id || novel.is_public = true)"
	ownerOnly := "@request.auth.id != '' && novel.owner = @request.auth.id"
	c.ListRule = types.Pointer(visible)
	c.ViewRule = types.Pointer(visible)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "novel", Required: true, CollectionId: novels.Id, MaxSelect: 1, CascadeDelete: true})
	c.Fields.Add(&core.NumberField{Name: "chapter_order", Required: true})
	c.Fields.Add(&core.TextField{Name: "title", Max: 500})
	c.Fields.Add(&core.TextField{Name: "translated_title", Max: 500})
	c.Fields.Add(&core.EditorField{Name: "original_content"})
	c.Fields.Add(&core.EditorField{Name: "translated_content"})
	c.Fields.Add(&core.EditorField{Name: "refined_content"})
	c.Fields.Add(&core.SelectField{Name: "status", Values: []string{"pending", "processing", "translated", "refined", "done", "failed"}, MaxSelect: 1})
	c.Fields.Add(&core.EditorField{Name: "error_message"})
	c.Fields.Add(&core.NumberField{Name: "original_char_count"})
	c.Fields.Add(&core.NumberField{Name: "translated_char_count"})
	c.Fields.Add(&core.NumberField{Name: "refined_char_count"})
	addSystemDateFields(c)
	c.AddIndex("idx_chapters_novel_order_unique", true, "novel,chapter_order", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureJobsCollection(users, novels *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(JobsCollection); err == nil {
		c, err := s.migrateSystemDateFields(existing)
		if err != nil {
			return nil, err
		}
		for _, field := range []core.Field{
			&core.BoolField{Name: "auto_segment_enabled"},
			&core.BoolField{Name: "auto_segment_active"},
			&core.NumberField{Name: "auto_segment_count"},
			&core.NumberField{Name: "auto_segment_current_index"},
			&core.NumberField{Name: "auto_segment_completed_count"},
			&core.TextField{Name: "auto_segment_chapter_id", Max: 64},
			&core.TextField{Name: "auto_segment_chapter_title", Max: 500},
		} {
			if err := s.ensureField(c, field); err != nil {
				return nil, err
			}
		}
		if opField := c.Fields.GetByName("operation"); opField != nil {
			if sel, ok := opField.(*core.SelectField); ok {
				hasDownload := false
				for _, v := range sel.Values {
					if v == "download" {
						hasDownload = true
						break
					}
				}
				if !hasDownload {
					sel.Values = append(sel.Values, "download")
					if err := s.App.Save(c); err != nil {
						return nil, err
					}
				}
			}
		}
		if f := c.Fields.GetByName("options_json"); f != nil {
			if tf, ok := f.(*core.TextField); ok && tf.Max < 10000000 {
				tf.Max = 10000000
				if err := s.App.Save(c); err != nil {
					return nil, err
				}
			}
		}
		if f := c.Fields.GetByName("chapter_ids"); f != nil {
			if tf, ok := f.(*core.TextField); ok && tf.Max < 10000000 {
				tf.Max = 10000000
				if err := s.App.Save(c); err != nil {
					return nil, err
				}
			}
		}
		return c, nil
	}
	c := core.NewBaseCollection(JobsCollection)
	ownerOnly := "@request.auth.id != '' && owner = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = nil
	c.Fields.Add(&core.RelationField{Name: "owner", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.RelationField{Name: "novel", Required: true, CollectionId: novels.Id, MaxSelect: 1, CascadeDelete: true})
	c.Fields.Add(&core.SelectField{Name: "status", Values: []string{"pending", "running", "done", "cancelled", "failed"}, MaxSelect: 1})
	c.Fields.Add(&core.SelectField{Name: "operation", Values: []string{"translate", "refine", "download"}, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "provider", Max: 120})
	c.Fields.Add(&core.TextField{Name: "model", Max: 200})
	c.Fields.Add(&core.TextField{Name: "chapter_ids", Max: 10000000})
	c.Fields.Add(&core.TextField{Name: "options_json", Max: 10000000})
	c.Fields.Add(&core.EditorField{Name: "error_message"})
	c.Fields.Add(&core.NumberField{Name: "total_chapters"})
	c.Fields.Add(&core.NumberField{Name: "completed_chapters"})
	c.Fields.Add(&core.NumberField{Name: "failed_chapters"})
	c.Fields.Add(&core.BoolField{Name: "auto_segment_enabled"})
	c.Fields.Add(&core.BoolField{Name: "auto_segment_active"})
	c.Fields.Add(&core.NumberField{Name: "auto_segment_count"})
	c.Fields.Add(&core.NumberField{Name: "auto_segment_current_index"})
	c.Fields.Add(&core.NumberField{Name: "auto_segment_completed_count"})
	c.Fields.Add(&core.TextField{Name: "auto_segment_chapter_id", Max: 64})
	c.Fields.Add(&core.TextField{Name: "auto_segment_chapter_title", Max: 500})
	addSystemDateFields(c)
	c.AddIndex("idx_jobs_owner", false, "owner", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

// epubFileMaxSize overrides PocketBase's 5MB default for the epubs "file"
// field, since exported epubs for long novels (1000+ chapters) can easily
// exceed that.
const epubFileMaxSize int64 = 200 << 20 // 200MB

func (s *Store) ensureEpubsCollection(novels *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(EpubsCollection); err == nil {
		c, err := s.migrateSystemDateFields(existing)
		if err != nil {
			return nil, err
		}
		return s.migrateEpubFileMaxSize(c)
	}
	c := core.NewBaseCollection(EpubsCollection)
	ownerOnly := "@request.auth.id != '' && novel.owner = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "novel", Required: true, CollectionId: novels.Id, MaxSelect: 1, CascadeDelete: true})
	c.Fields.Add(&core.SelectField{Name: "file_kind", Values: []string{"original", "translated"}, MaxSelect: 1})
	c.Fields.Add(&core.TextField{Name: "source_variant", Max: 64})
	c.Fields.Add(&core.TextField{Name: "label", Max: 250})
	c.Fields.Add(&core.FileField{Name: "file", Required: true, MaxSelect: 1, MaxSize: epubFileMaxSize})
	addSystemDateFields(c)
	c.AddIndex("idx_epubs_unique_variant", true, "novel,file_kind,source_variant", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

// migrateEpubFileMaxSize raises the max upload size of the "file" field on
// pre-existing epubs collections that were created before epubFileMaxSize
// was introduced (they default to PocketBase's 5MB limit).
func (s *Store) migrateEpubFileMaxSize(c *core.Collection) (*core.Collection, error) {
	field, ok := c.Fields.GetByName("file").(*core.FileField)
	if !ok || field.MaxSize >= epubFileMaxSize {
		return c, nil
	}
	field.MaxSize = epubFileMaxSize
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) ensureReadingProgressCollection(users, novels *core.Collection) (*core.Collection, error) {
	if existing, err := s.App.FindCollectionByNameOrId(ReadingProgressCollection); err == nil {
		return existing, nil
	}
	c := core.NewBaseCollection(ReadingProgressCollection)
	ownerOnly := "@request.auth.id != '' && user = @request.auth.id"
	c.ListRule = types.Pointer(ownerOnly)
	c.ViewRule = types.Pointer(ownerOnly)
	c.CreateRule = types.Pointer(ownerOnly)
	c.UpdateRule = types.Pointer(ownerOnly)
	c.DeleteRule = types.Pointer(ownerOnly)
	c.Fields.Add(&core.RelationField{Name: "user", Required: true, CollectionId: users.Id, MaxSelect: 1})
	c.Fields.Add(&core.RelationField{Name: "novel", Required: true, CollectionId: novels.Id, MaxSelect: 1, CascadeDelete: true})
	c.Fields.Add(&core.TextField{Name: "chapter_id", Max: 64})
	c.Fields.Add(&core.NumberField{Name: "scroll_percent"})
	addSystemDateFields(c)
	c.AddIndex("idx_reading_progress_user_novel_unique", true, "user,novel", "")
	if err := s.App.Save(c); err != nil {
		return nil, err
	}
	return c, nil
}

func (s *Store) seedProviders() error {
	collection, err := s.App.FindCollectionByNameOrId(ProvidersCollection)
	if err != nil {
		return err
	}
	supported := make(map[string]struct{}, len(ai.Providers()))
	for _, info := range ai.Providers() {
		supported[info.ID] = struct{}{}
		record, err := s.App.FindFirstRecordByFilter(ProvidersCollection, "key = {:key}", dbx.Params{"key": info.ID})
		if err != nil {
			record = core.NewRecord(collection)
		}
		modelsJSON, _ := json.Marshal(info.Models)
		record.Set("key", info.ID)
		record.Set("label", info.Name)
		record.Set("base_url", info.BaseURL)
		record.Set("default_model", info.DefaultModel)
		record.Set("kind", providerKind(info))
		record.Set("models_json", string(modelsJSON))
		record.Set("enabled", true)
		if err := s.App.Save(record); err != nil {
			return err
		}
	}
	existing, err := s.App.FindRecordsByFilter(ProvidersCollection, "", "", 200, 0)
	if err != nil {
		return err
	}
	for _, record := range existing {
		if _, ok := supported[record.GetString("key")]; ok {
			continue
		}
		record.Set("enabled", false)
		if err := s.App.Save(record); err != nil {
			return err
		}
	}
	return nil
}
