package store

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/filesystem"
)

func (s *Store) CreateNovel(ownerID string, novel *Novel) error {
	novel.Status = normalizeNovelStatus(novel.Status)
	novel.Tags = jsonString(parseNovelTagsJSON(novel.Tags), "[]")
	collection, err := s.App.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		return err
	}
	record := core.NewRecord(collection)
	record.Set("owner", ownerID)
	applyNovelToRecord(record, novel)
	if err := s.App.Save(record); err != nil {
		return err
	}
	stored, err := s.GetNovelAccessible(ownerID, record.Id)
	if err != nil {
		return err
	}
	*novel = *stored
	return nil
}

func (s *Store) ListNovels(userID string, limit int) ([]Novel, error) {
	if limit <= 0 || limit > 200 {
		limit = 100
	}
	records, err := s.App.FindRecordsByFilter(NovelsCollection, "owner = {:owner} || is_public = true", "-created", limit, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	out := make([]Novel, 0, len(records))
	for _, record := range records {
		out = append(out, s.novelFromRecord(record))
	}
	return out, nil
}

func (s *Store) ListOwnedNovelsWithURL(ownerID string) ([]Novel, error) {
	const pageSize = 200
	var out []Novel
	offset := 0
	for {
		records, err := s.App.FindRecordsByFilter(NovelsCollection, "owner = {:owner} && url != '' && status != 'completed' && status != 'cancelled'", "-created", pageSize, offset, dbx.Params{"owner": ownerID})
		if err != nil {
			return nil, err
		}
		for _, record := range records {
			out = append(out, s.novelFromRecord(record))
		}
		if len(records) < pageSize {
			break
		}
		offset += pageSize
	}
	if out == nil {
		out = []Novel{}
	}
	return out, nil
}

func (s *Store) ListOwnedNovelsWithTranslationStats(ownerID string) ([]Novel, error) {
	const pageSize = 200
	var out []Novel
	offset := 0
	for {
		records, err := s.App.FindRecordsByFilter(NovelsCollection, "owner = {:owner} && status != 'cancelled'", "-updated", pageSize, offset, dbx.Params{"owner": ownerID})
		if err != nil {
			return nil, err
		}
		for _, record := range records {
			out = append(out, s.novelFromRecord(record))
		}
		if len(records) < pageSize {
			break
		}
		offset += pageSize
	}
	if out == nil {
		out = []Novel{}
	}
	return out, nil
}

func (s *Store) GetOwnedNovelChapterIDsByStatus(userID, novelID string) (pendingIDs []string, err error) {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return nil, err
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel} && (status = 'pending' || (original_content != '' && translated_content = ''))", "chapter_order", 5000, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, err
	}
	ids := make([]string, 0, len(records))
	for _, record := range records {
		ids = append(ids, record.Id)
	}
	return ids, nil
}

func (s *Store) GetNovelAccessible(userID, novelID string) (*Novel, error) {
	record, err := s.App.FindRecordById(NovelsCollection, novelID)
	if err != nil {
		return nil, ErrNotFound
	}
	if record.GetString("owner") != userID && !record.GetBool("is_public") {
		return nil, ErrNotFound
	}
	novel := s.novelFromRecord(record)
	return &novel, nil
}

func (s *Store) GetOwnedNovel(userID, novelID string) (*Novel, error) {
	record, err := s.App.FindRecordById(NovelsCollection, novelID)
	if err != nil {
		return nil, ErrNotFound
	}
	if record.GetString("owner") != userID {
		return nil, ErrForbidden
	}
	novel := s.novelFromRecord(record)
	return &novel, nil
}

func (s *Store) UpdateNovel(userID, novelID string, patch map[string]any) (*Novel, error) {
	record, err := s.App.FindRecordById(NovelsCollection, novelID)
	if err != nil {
		return nil, ErrNotFound
	}
	if record.GetString("owner") != userID {
		return nil, ErrForbidden
	}
	for key, value := range patch {
		switch key {
		case "sourceLanguage":
			record.Set("source_language", value)
		case "targetLanguage":
			record.Set("target_language", value)
		case "sourceTitle":
			record.Set("source_title", value)
		case "sourceAuthor":
			record.Set("source_author", value)
		case "sourceDescription":
			record.Set("source_description", value)
		case "sourceSeries":
			record.Set("source_series", value)
		case "sourceNumber":
			record.Set("source_number", value)
		case "targetTitle":
			record.Set("target_title", value)
		case "targetAuthor":
			record.Set("target_author", value)
		case "targetDescription":
			record.Set("target_description", value)
		case "targetSeries":
			record.Set("target_series", value)
		case "targetNumber":
			record.Set("target_number", value)
		case "glossary":
			record.Set("glossary", jsonString(value, "[]"))
		case "prompts":
			overrides := ParseNovelPromptOverrides(value)
			record.Set("translation_system_prompt", overrides.Translation.SystemPrompt)
			record.Set("translation_user_prompt", overrides.Translation.UserPrompt)
			record.Set("refine_system_prompt", overrides.Refine.SystemPrompt)
			record.Set("refine_user_prompt", overrides.Refine.UserPrompt)
			record.Set("check_system_prompt", overrides.Check.SystemPrompt)
			record.Set("check_user_prompt", overrides.Check.UserPrompt)
		case "notes":
			record.Set("notes", value)
		case "aiOptions":
			record.Set("ai_options", jsonString(value, "{}"))
		case "translationOptions":
			record.Set("translation_options", jsonString(value, "{}"))
		case "cleanupRules":
			record.Set("cleanup_rules", jsonString(value, "[]"))
		case "url":
			record.Set("url", value)
		case "customCommands":
			record.Set("custom_commands", value)
		case "status":
			record.Set("status", normalizeNovelStatus(fmt.Sprint(value)))
		case "tags":
			record.Set("tags", jsonString(normalizeNovelTagsValue(value), "[]"))
		case "isPublic":
			record.Set("is_public", value)
		}
	}
	if err := s.App.Save(record); err != nil {
		return nil, err
	}
	updated := s.novelFromRecord(record)
	return &updated, nil
}

func (s *Store) DeleteNovel(userID, novelID string) error {
	record, err := s.App.FindRecordById(NovelsCollection, novelID)
	if err != nil {
		return ErrNotFound
	}
	if record.GetString("owner") != userID {
		return ErrForbidden
	}
	return s.App.Delete(record)
}

func (s *Store) SetNovelVisibility(userID, novelID string, isPublic bool) (*Novel, error) {
	return s.UpdateNovel(userID, novelID, map[string]any{"isPublic": isPublic})
}

func (s *Store) ListNovelTagSuggestions(userID, query string, limit int) ([]string, error) {
	if limit <= 0 || limit > 200 {
		limit = 100
	}
	records, err := s.App.FindRecordsByFilter(NovelsCollection, "owner = {:owner}", "-updated", 5000, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	query = strings.ToLower(strings.TrimSpace(query))
	seen := make(map[string]string)
	for _, record := range records {
		for _, tag := range parseNovelTagsJSON(record.GetString("tags")) {
			if query != "" && !strings.Contains(strings.ToLower(tag), query) {
				continue
			}
			key := strings.ToLower(tag)
			if _, ok := seen[key]; ok {
				continue
			}
			seen[key] = tag
		}
	}
	out := make([]string, 0, len(seen))
	for _, tag := range seen {
		out = append(out, tag)
	}
	sort.SliceStable(out, func(i, j int) bool {
		left := strings.ToLower(out[i])
		right := strings.ToLower(out[j])
		leftPrefix := query != "" && strings.HasPrefix(left, query)
		rightPrefix := query != "" && strings.HasPrefix(right, query)
		if leftPrefix != rightPrefix {
			return leftPrefix
		}
		return left < right
	})
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

func (s *Store) ListNovelSeriesSuggestions(userID, query string, limit int) ([]string, error) {
	if limit <= 0 || limit > 200 {
		limit = 100
	}
	records, err := s.App.FindRecordsByFilter(NovelsCollection, "owner = {:owner}", "-updated", 5000, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	query = strings.ToLower(strings.TrimSpace(query))
	seen := make(map[string]string)
	for _, record := range records {
		for _, field := range []string{"source_series", "target_series"} {
			series := strings.TrimSpace(record.GetString(field))
			if series == "" {
				continue
			}
			if query != "" && !strings.Contains(strings.ToLower(series), query) {
				continue
			}
			key := strings.ToLower(series)
			if _, ok := seen[key]; ok {
				continue
			}
			seen[key] = series
		}
	}
	out := make([]string, 0, len(seen))
	for _, series := range seen {
		out = append(out, series)
	}
	sort.SliceStable(out, func(i, j int) bool {
		left := strings.ToLower(out[i])
		right := strings.ToLower(out[j])
		leftPrefix := query != "" && strings.HasPrefix(left, query)
		rightPrefix := query != "" && strings.HasPrefix(right, query)
		if leftPrefix != rightPrefix {
			return leftPrefix
		}
		return left < right
	})
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

func (s *Store) CopyNovel(userID, novelID string) (*Novel, error) {
	novel, err := s.GetNovelAccessible(userID, novelID)
	if err != nil {
		return nil, err
	}
	clone := *novel
	clone.ID = ""
	clone.OwnerID = userID
	clone.IsPublic = false
	clone.CoverPath = ""
	clone.CoverFile = ""
	clone.ChapterCount = 0
	clone.TranslatedCount = 0
	clone.CompletedCount = 0
	clone.OriginalCharCount = 0
	clone.TranslatedCharCount = 0
	clone.RefinedCharCount = 0
	clone.TotalCharCount = 0
	clone.MaxChapterOrder = 0
	if err := s.CreateNovel(userID, &clone); err != nil {
		return nil, err
	}
	chapters, err := s.ListChaptersAccessible(userID, novelID)
	if err != nil {
		return nil, err
	}
	for _, chapter := range chapters {
		chapter.ID = ""
		chapter.NovelID = clone.ID
		if _, err := s.UpsertChapterWithoutStats(userID, clone.ID, &chapter); err != nil {
			return nil, err
		}
	}
	if err := s.RecalculateNovelStats(clone.ID); err != nil {
		return nil, err
	}
	freshClone, err := s.GetOwnedNovel(userID, clone.ID)
	if err != nil {
		return nil, err
	}
	return freshClone, nil
}

func (s *Store) ImportEpubNovel(input *ImportEpubNovelInput) (*ImportEpubNovelResult, error) {
	if input == nil {
		return nil, fmt.Errorf("import input required")
	}
	resultNovel := &Novel{
		SourceLanguage:     input.SourceLanguage,
		TargetLanguage:     input.TargetLanguage,
		SourceTitle:        input.SourceTitle,
		SourceAuthor:       clampText(input.SourceAuthor, 250),
		SourceDescription:  clampText(input.SourceDescription, 5000),
		SourceSeries:       input.SourceSeries,
		SourceNumber:       input.SourceNumber,
		Status:             "completed",
		Tags:               "[]",
		Glossary:           "[]",
		AIOptions:          "{}",
		TranslationOptions: "{}",
		CleanupRules:       "[]",
	}
	if err := s.CreateNovel(input.OwnerID, resultNovel); err != nil {
		return nil, err
	}
	if len(input.CoverBlob) > 0 {
		if err := s.attachNovelCover(resultNovel.ID, input.CoverBlob, input.CoverMime); err != nil {
			return nil, err
		}
	}
	for idx, chapter := range input.Chapters {
		_, err := s.UpsertChapterWithoutStats(input.OwnerID, resultNovel.ID, &Chapter{
			ChapterOrder:    idx + 1,
			Title:           clampText(chapter.Title, 500),
			OriginalContent: chapter.Content,
			Status:          "pending",
		})
		if err != nil {
			return nil, err
		}
	}
	if err := s.RecalculateNovelStats(resultNovel.ID); err != nil {
		return nil, err
	}
	epub, err := s.UpsertEpub(input.OwnerID, &Epub{NovelID: resultNovel.ID, FileKind: "original", SourceVariant: "original", Label: "EPUB original"}, input.FileName, input.MimeType, input.FileBlob)
	if err != nil {
		return nil, err
	}
	fresh, err := s.GetOwnedNovel(input.OwnerID, resultNovel.ID)
	if err != nil {
		return nil, err
	}
	*resultNovel = *fresh
	return &ImportEpubNovelResult{Novel: *resultNovel, Epub: *epub, ChaptersImported: len(input.Chapters)}, nil
}

func (s *Store) ImportUrlNovel(input *ImportUrlNovelInput) (*ImportUrlNovelResult, error) {
	if input == nil {
		return nil, fmt.Errorf("import input required")
	}
	novel := &Novel{
		URL:                input.URL,
		SourceLanguage:     input.SourceLanguage,
		SourceTitle:        strings.TrimSpace(input.SourceTitle),
		SourceAuthor:       clampText(input.SourceAuthor, 250),
		SourceDescription:  clampText(input.SourceDescription, 5000),
		TargetLanguage:     input.TargetLanguage,
		Status:             "ongoing",
		Tags:               "[]",
		Glossary:           "[]",
		AIOptions:          "{}",
		TranslationOptions: "{}",
		CleanupRules:       "[]",
	}
	if err := s.CreateNovel(input.OwnerID, novel); err != nil {
		return nil, err
	}
	fresh, err := s.GetOwnedNovel(input.OwnerID, novel.ID)
	if err != nil {
		return nil, err
	}
	*novel = *fresh
	return &ImportUrlNovelResult{Novel: *novel, ChaptersImported: 0}, nil
}

func (s *Store) ImportZipNovel(input *ImportZipNovelInput) (*ImportZipNovelResult, error) {
	if input == nil {
		return nil, fmt.Errorf("import input required")
	}
	meta := struct {
		SourceLanguage    string `json:"sourceLanguage"`
		TargetLanguage    string `json:"targetLanguage"`
		URL               string `json:"url"`
		SourceTitle       string `json:"sourceTitle"`
		SourceAuthor      string `json:"sourceAuthor"`
		SourceDescription string `json:"sourceDescription"`
		TargetTitle       string `json:"targetTitle"`
		TargetAuthor      string `json:"targetAuthor"`
		TargetDescription string `json:"targetDescription"`
		SourceSeries      string `json:"sourceSeries"`
		SourceNumber      string `json:"sourceNumber"`
		TargetSeries      string `json:"targetSeries"`
		TargetNumber      string `json:"targetNumber"`
		Notes             string `json:"notes"`
		CustomCommands    string `json:"customCommands"`
		Status            string `json:"status"`
		IsPublic          bool   `json:"isPublic"`
	}{}
	if err := json.Unmarshal([]byte(input.MetadataJSON), &meta); err != nil {
		return nil, fmt.Errorf("invalid metadata.json: %w", err)
	}
	canonicalSourceTitle := strings.TrimSpace(meta.SourceTitle)
	canonicalSourceAuthor := clampText(meta.SourceAuthor, 250)
	canonicalSourceDescription := clampText(meta.SourceDescription, 5000)
	if canonicalSourceTitle == "" {
		return nil, fmt.Errorf("sourceTitle is required in metadata.json")
	}
	if meta.SourceLanguage == "" {
		return nil, fmt.Errorf("sourceLanguage is required in metadata.json")
	}
	if meta.TargetLanguage == "" {
		return nil, fmt.Errorf("targetLanguage is required in metadata.json")
	}
	resultNovel := &Novel{
		SourceLanguage:     meta.SourceLanguage,
		TargetLanguage:     meta.TargetLanguage,
		URL:                meta.URL,
		SourceTitle:        canonicalSourceTitle,
		SourceAuthor:       canonicalSourceAuthor,
		SourceDescription:  canonicalSourceDescription,
		SourceSeries:       meta.SourceSeries,
		SourceNumber:       meta.SourceNumber,
		TargetTitle:        meta.TargetTitle,
		TargetAuthor:       meta.TargetAuthor,
		TargetDescription:  meta.TargetDescription,
		TargetSeries:       meta.TargetSeries,
		TargetNumber:       meta.TargetNumber,
		Notes:              meta.Notes,
		CustomCommands:     meta.CustomCommands,
		Status:             normalizeNovelStatus(meta.Status),
		Tags:               "[]",
		IsPublic:           meta.IsPublic,
		Glossary:           "[]",
		AIOptions:          "{}",
		TranslationOptions: "{}",
		CleanupRules:       "[]",
	}
	if err := s.CreateNovel(input.OwnerID, resultNovel); err != nil {
		return nil, err
	}
	if len(input.CoverBlob) > 0 {
		if err := s.attachNovelCover(resultNovel.ID, input.CoverBlob, input.CoverMime); err != nil {
			return nil, err
		}
	}
	for _, chapter := range input.Chapters {
		status := "pending"
		if strings.TrimSpace(chapter.TranslatedContent) != "" {
			status = "translated"
		}
		_, err := s.UpsertChapterWithoutStats(input.OwnerID, resultNovel.ID, &Chapter{
			ChapterOrder:      chapter.Order,
			Title:             chapter.Title,
			TranslatedTitle:   chapter.TranslatedTitle,
			OriginalContent:   chapter.OriginalContent,
			TranslatedContent: chapter.TranslatedContent,
			Status:            status,
		})
		if err != nil {
			return nil, err
		}
	}
	if err := s.RecalculateNovelStats(resultNovel.ID); err != nil {
		return nil, err
	}
	fresh, err := s.GetOwnedNovel(input.OwnerID, resultNovel.ID)
	if err != nil {
		return nil, err
	}
	*resultNovel = *fresh
	return &ImportZipNovelResult{Novel: *resultNovel, ChaptersImported: len(input.Chapters)}, nil
}

func (s *Store) attachNovelCover(novelID string, blob []byte, mimeType string) error {
	collection, err := s.App.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		return err
	}
	record, err := s.App.FindRecordById(collection, novelID)
	if err != nil {
		return err
	}
	ext := coverExtension(mimeType)
	name := "cover" + ext
	file, err := filesystem.NewFileFromBytes(blob, name)
	if err != nil {
		return err
	}
	record.Set("cover", []*filesystem.File{file})
	return s.App.Save(record)
}

func (s *Store) AttachCoverBlob(novelID string, blob []byte, mimeType string) error {
	return s.attachNovelCover(novelID, blob, mimeType)
}

func (s *Store) UpdateNovelCover(userID, novelID string, blob []byte, mimeType string) (*Novel, error) {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return nil, err
	}
	if err := s.attachNovelCover(novelID, blob, mimeType); err != nil {
		return nil, err
	}
	return s.GetOwnedNovel(userID, novelID)
}

func coverExtension(mimeType string) string {
	switch strings.ToLower(strings.TrimSpace(mimeType)) {
	case "image/jpeg", "image/jpg":
		return ".jpg"
	case "image/png":
		return ".png"
	case "image/gif":
		return ".gif"
	case "image/webp":
		return ".webp"
	case "image/svg+xml":
		return ".svg"
	}
	return ".jpg"
}
