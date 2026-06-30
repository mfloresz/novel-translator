package store

import (
	"encoding/json"
	"strings"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

func (s *Store) ListChaptersAccessible(userID, novelID string) ([]Chapter, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return nil, err
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "chapter_order", 5000, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, err
	}
	out := make([]Chapter, 0, len(records))
	for _, record := range records {
		out = append(out, chapterFromRecord(record))
	}
	return out, nil
}

func (s *Store) ListAllChapterSummariesAccessible(userID, novelID string) ([]ChapterSummary, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return nil, err
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "chapter_order", 5000, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, err
	}
	out := make([]ChapterSummary, 0, len(records))
	for _, record := range records {
		out = append(out, chapterSummaryFromRecord(record))
	}
	return out, nil
}

func (s *Store) ListChapterSummariesAccessible(userID, novelID string, limit, offset int) ([]ChapterSummary, int, error) {
	novel, err := s.GetNovelAccessible(userID, novelID)
	if err != nil {
		return nil, 0, err
	}
	if limit <= 0 {
		limit = 50
	}
	if limit > 5000 {
		limit = 5000
	}
	if offset < 0 {
		offset = 0
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "chapter_order", limit, offset, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, 0, err
	}
	out := make([]ChapterSummary, 0, len(records))
	for _, record := range records {
		out = append(out, chapterSummaryFromRecord(record))
	}
	return out, novel.ChapterCount, nil
}

func (s *Store) GetChapterStatsAccessible(userID, novelID string) (*ChapterStats, error) {
	novel, err := s.GetNovelAccessible(userID, novelID)
	if err != nil {
		return nil, err
	}
	return &ChapterStats{
		TotalChapters:        novel.ChapterCount,
		CompletedChapters:    novel.CompletedCount,
		TranslatedChapters:   novel.TranslatedCount,
		OriginalCharacters:   novel.OriginalCharCount,
		TranslatedCharacters: novel.TranslatedCharCount,
		RefinedCharacters:    novel.RefinedCharCount,
		TotalCharacters:      novel.TotalCharCount,
		MaxChapterOrder:      novel.MaxChapterOrder,
	}, nil
}

func (s *Store) RecalculateNovelStats(novelID string) error {
	novelRecord, err := s.App.FindRecordById(NovelsCollection, novelID)
	if err != nil {
		return ErrNotFound
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "", 5000, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return err
	}
	stats := &ChapterStats{}
	for _, record := range records {
		stats.TotalChapters++
		order := asInt(record.GetFloat("chapter_order"), 0)
		if order > stats.MaxChapterOrder {
			stats.MaxChapterOrder = order
		}
		status := record.GetString("status")
		if status == "translated" || status == "refined" || status == "done" {
			stats.TranslatedChapters++
		}
		if status == "refined" || status == "done" {
			stats.CompletedChapters++
		}
		originalChars, translatedChars, refinedChars := charCountsFromRecord(record)
		stats.OriginalCharacters += originalChars
		stats.TranslatedCharacters += translatedChars
		stats.RefinedCharacters += refinedChars
	}
	stats.TotalCharacters = stats.OriginalCharacters + stats.TranslatedCharacters + stats.RefinedCharacters
	novelRecord.Set("chapter_count", stats.TotalChapters)
	novelRecord.Set("translated_count", stats.TranslatedChapters)
	novelRecord.Set("completed_count", stats.CompletedChapters)
	novelRecord.Set("original_char_count", stats.OriginalCharacters)
	novelRecord.Set("translated_char_count", stats.TranslatedCharacters)
	novelRecord.Set("refined_char_count", stats.RefinedCharacters)
	novelRecord.Set("total_char_count", stats.TotalCharacters)
	novelRecord.Set("max_chapter_order", stats.MaxChapterOrder)
	return s.App.Save(novelRecord)
}

func (s *Store) BackfillChapterCharCounts() error {
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "", "", 5000, 0)
	if err != nil {
		return err
	}
	for _, record := range records {
		setCharCounts(record, record.GetString("original_content"), record.GetString("translated_content"), record.GetString("refined_content"))
		if err := s.App.Save(record); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) BackfillNovelStats() error {
	novels, err := s.App.FindRecordsByFilter(NovelsCollection, "", "", 5000, 0)
	if err != nil {
		return err
	}
	for _, novel := range novels {
		if err := s.RecalculateNovelStats(novel.Id); err != nil {
			return err
		}
	}
	return nil
}

func setCharCounts(record *core.Record, original, translated, refined string) {
	record.Set("original_char_count", len(original))
	record.Set("translated_char_count", len(translated))
	record.Set("refined_char_count", len(refined))
}

func charCountsFromRecord(record *core.Record) (original, translated, refined int) {
	return asInt(record.GetFloat("original_char_count"), 0),
		asInt(record.GetFloat("translated_char_count"), 0),
		asInt(record.GetFloat("refined_char_count"), 0)
}

func chapterSummaryFromRecord(record *core.Record) ChapterSummary {
	original := record.GetString("original_content")
	translated := record.GetString("translated_content")
	refined := record.GetString("refined_content")
	originalChars, translatedChars, refinedChars := charCountsFromRecord(record)
	return ChapterSummary{
		ID:                   record.Id,
		NovelID:              record.GetString("novel"),
		ChapterOrder:         asInt(record.GetFloat("chapter_order"), 0),
		Title:                record.GetString("title"),
		TranslatedTitle:      record.GetString("translated_title"),
		Status:               defaultString(record.GetString("status"), "pending"),
		ErrorMessage:         record.GetString("error_message"),
		HasOriginalContent:   strings.TrimSpace(original) != "",
		HasTranslatedContent: strings.TrimSpace(translated) != "",
		HasRefinedContent:    strings.TrimSpace(refined) != "",
		OriginalChars:        originalChars,
		TranslatedChars:      translatedChars,
		RefinedChars:         refinedChars,
		CreatedAt:            record.GetDateTime("created").String(),
		UpdatedAt:            record.GetDateTime("updated").String(),
	}
}

func (s *Store) GetChapterAccessible(userID, novelID, chapterID string) (*Chapter, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return nil, err
	}
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil || record.GetString("novel") != novelID {
		return nil, ErrNotFound
	}
	chapter := chapterFromRecord(record)
	return &chapter, nil
}

func (s *Store) UpsertChapter(userID, novelID string, chapter *Chapter) (*Chapter, error) {
	return s.upsertChapter(userID, novelID, chapter, true)
}

func (s *Store) UpsertChapterWithoutStats(userID, novelID string, chapter *Chapter) (*Chapter, error) {
	return s.upsertChapter(userID, novelID, chapter, false)
}

func (s *Store) upsertChapter(userID, novelID string, chapter *Chapter, recalcStats bool) (*Chapter, error) {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return nil, err
	}
	var record *core.Record
	var err error
	if strings.TrimSpace(chapter.ID) != "" {
		record, err = s.App.FindRecordById(ChaptersCollection, chapter.ID)
		if err != nil {
			return nil, ErrNotFound
		}
		if record.GetString("novel") != novelID {
			return nil, ErrForbidden
		}
	} else {
		collection, cErr := s.App.FindCollectionByNameOrId(ChaptersCollection)
		if cErr != nil {
			return nil, cErr
		}
		record = core.NewRecord(collection)
		record.Set("novel", novelID)
	}
	status := strings.TrimSpace(chapter.Status)
	if status == "" {
		status = record.GetString("status")
	}
	if status == "" {
		status = "pending"
	}

	record.Set("chapter_order", chapter.ChapterOrder)
	record.Set("title", chapter.Title)
	record.Set("translated_title", chapter.TranslatedTitle)
	record.Set("original_content", chapter.OriginalContent)
	record.Set("translated_content", chapter.TranslatedContent)
	record.Set("refined_content", chapter.RefinedContent)
	setCharCounts(record, chapter.OriginalContent, chapter.TranslatedContent, chapter.RefinedContent)
	record.Set("status", status)
	record.Set("error_message", chapter.ErrorMessage)
	if err := s.App.Save(record); err != nil {
		return nil, err
	}
	if recalcStats {
		if err := s.RecalculateNovelStats(novelID); err != nil {
			return nil, err
		}
	}
	stored := chapterFromRecord(record)
	return &stored, nil
}

func (s *Store) DeleteChapter(userID, novelID, chapterID string) error {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return err
	}
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil || record.GetString("novel") != novelID {
		return ErrNotFound
	}
	if err := s.App.Delete(record); err != nil {
		return err
	}
	if err := s.removeDeletedChapterReferences(novelID, []string{chapterID}); err != nil {
		return err
	}
	return s.RecalculateNovelStats(novelID)
}

func (s *Store) BulkDeleteChapters(userID, novelID string, ids []string) (int, error) {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return 0, err
	}
	deleted := 0
	deletedIDs := make([]string, 0, len(ids))
	for _, id := range ids {
		record, err := s.App.FindRecordById(ChaptersCollection, id)
		if err != nil || record.GetString("novel") != novelID {
			continue
		}
		if err := s.App.Delete(record); err != nil {
			return deleted, err
		}
		deleted++
		deletedIDs = append(deletedIDs, id)
	}
	if err := s.removeDeletedChapterReferences(novelID, deletedIDs); err != nil {
		return deleted, err
	}
	if err := s.RecalculateNovelStats(novelID); err != nil {
		return deleted, err
	}
	return deleted, nil
}

func (s *Store) UpdateChapterStatus(chapterID, status, errorMessage string) error {
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil {
		return ErrNotFound
	}
	record.Set("status", status)
	record.Set("error_message", errorMessage)
	if err := s.App.Save(record); err != nil {
		return err
	}
	return s.RecalculateNovelStats(record.GetString("novel"))
}

func (s *Store) UpdateChapterStatusForUser(userID, novelID, chapterID, status, errorMessage string) error {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return err
	}
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil || record.GetString("novel") != novelID {
		return ErrNotFound
	}
	record.Set("status", status)
	record.Set("error_message", errorMessage)
	if err := s.App.Save(record); err != nil {
		return err
	}
	return s.RecalculateNovelStats(novelID)
}

func (s *Store) SaveChapterTranslation(chapterID, translatedTitle, translatedContent, refinedContent, status string) error {
	return s.saveChapterTranslation(chapterID, translatedTitle, translatedContent, refinedContent, status, true)
}

func (s *Store) SaveChapterTranslationFast(chapterID, translatedTitle, translatedContent, refinedContent, status string) error {
	return s.saveChapterTranslation(chapterID, translatedTitle, translatedContent, refinedContent, status, false)
}

func (s *Store) saveChapterTranslation(chapterID, translatedTitle, translatedContent, refinedContent, status string, recalcStats bool) error {
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil {
		return ErrNotFound
	}
	if translatedTitle != "" {
		record.Set("translated_title", translatedTitle)
	}
	if translatedContent != "" {
		record.Set("translated_content", translatedContent)
	}
	if refinedContent != "" {
		record.Set("refined_content", refinedContent)
	}
	if status != "" {
		record.Set("status", status)
	}
	record.Set("error_message", "")
	setCharCounts(record, record.GetString("original_content"), record.GetString("translated_content"), record.GetString("refined_content"))
	if err := s.App.Save(record); err != nil {
		return err
	}
	if !recalcStats {
		return nil
	}
	return s.RecalculateNovelStats(record.GetString("novel"))
}

func (s *Store) UpdateChapterStatusFast(chapterID, status, errorMessage string) error {
	record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
	if err != nil {
		return ErrNotFound
	}
	record.Set("status", status)
	record.Set("error_message", errorMessage)
	return s.App.Save(record)
}

func (s *Store) UpdateChaptersStatusFast(chapterIDs []string, status, errorMessage string) error {
	for _, chapterID := range chapterIDs {
		if strings.TrimSpace(chapterID) == "" {
			continue
		}
		record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
		if err != nil {
			continue
		}
		record.Set("status", status)
		record.Set("error_message", errorMessage)
		if err := s.App.Save(record); err != nil {
			return err
		}
	}
	return nil
}

func (s *Store) ReconcileProcessingChaptersForJob(jobID string) error {
	job, err := s.GetJob(jobID)
	if err != nil {
		return err
	}
	chapterIDs := []string{}
	if trimmed := strings.TrimSpace(job.ChapterIDs); trimmed != "" {
		if err := json.Unmarshal([]byte(trimmed), &chapterIDs); err != nil {
			return err
		}
	}
	mutated := false
	for _, chapterID := range chapterIDs {
		record, err := s.App.FindRecordById(ChaptersCollection, chapterID)
		if err != nil {
			continue
		}
		if record.GetString("status") != "processing" {
			continue
		}
		status := "pending"
		if strings.TrimSpace(record.GetString("refined_content")) != "" {
			status = "refined"
		} else if strings.TrimSpace(record.GetString("translated_content")) != "" {
			status = "translated"
		}
		record.Set("status", status)
		record.Set("error_message", "")
		if err := s.App.Save(record); err != nil {
			return err
		}
		mutated = true
	}
	if mutated {
		return s.RecalculateNovelStats(job.NovelID)
	}
	return nil
}

func (s *Store) GetMaxChapterOrder(userID, novelID string) (int, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return 0, err
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "-chapter_order", 1, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return 0, err
	}
	if len(records) == 0 {
		return 0, nil
	}
	return asInt(records[0].GetFloat("chapter_order"), 0), nil
}

func (s *Store) GetExistingChapterURLs(userID, novelID string) (map[string]bool, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return nil, err
	}
	records, err := s.App.FindRecordsByFilter(ChaptersCollection, "novel = {:novel}", "chapter_order", 5000, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, err
	}
	existing := make(map[string]bool, len(records))
	for _, record := range records {
		title := record.GetString("title")
		if title != "" {
			existing[title] = true
		}
	}
	return existing, nil
}
