package store

import (
	"github.com/pocketbase/pocketbase/core"
)

func userFromRecord(record *core.Record) User {
	return User{
		ID:        record.Id,
		Email:     record.Email(),
		Name:      record.GetString("name"),
		Theme:     defaultString(record.GetString("theme"), "system"),
		CreatedAt: record.GetString("created"),
		UpdatedAt: record.GetString("updated"),
	}
}

func (s *Store) novelFromRecord(record *core.Record) Novel {
	coverFile := firstString(record.GetStringSlice("cover"))
	return Novel{
		ID:                      record.Id,
		OwnerID:                 record.GetString("owner"),
		SourceLanguage:          record.GetString("source_language"),
		TargetLanguage:          record.GetString("target_language"),
		SourceTitle:             record.GetString("source_title"),
		SourceAuthor:            record.GetString("source_author"),
		SourceDescription:       record.GetString("source_description"),
		SourceSeries:            record.GetString("source_series"),
		SourceNumber:            record.GetString("source_number"),
		TargetTitle:             record.GetString("target_title"),
		TargetAuthor:            record.GetString("target_author"),
		TargetDescription:       record.GetString("target_description"),
		TargetSeries:            record.GetString("target_series"),
		TargetNumber:            record.GetString("target_number"),
		Glossary:                defaultString(record.GetString("glossary"), "[]"),
		TranslationSystemPrompt: record.GetString("translation_system_prompt"),
		TranslationUserPrompt:   record.GetString("translation_user_prompt"),
		RefineSystemPrompt:      record.GetString("refine_system_prompt"),
		RefineUserPrompt:        record.GetString("refine_user_prompt"),
		CheckSystemPrompt:       record.GetString("check_system_prompt"),
		CheckUserPrompt:         record.GetString("check_user_prompt"),
		Notes:                   record.GetString("notes"),
		AIOptions:               defaultString(record.GetString("ai_options"), "{}"),
		TranslationOptions:      defaultString(record.GetString("translation_options"), "{}"),
		CleanupRules:            defaultString(record.GetString("cleanup_rules"), "[]"),
		URL:                     record.GetString("url"),
		CustomCommands:          record.GetString("custom_commands"),
		Status:                  normalizeNovelStatus(record.GetString("status")),
		Tags:                    jsonString(parseNovelTagsJSON(record.GetString("tags")), "[]"),
		CoverFile:               coverFile,
		CoverPath:               buildPBFileURL(NovelsCollection, record.Id, coverFile),
		IsPublic:                record.GetBool("is_public"),
		ChapterCount:            asInt(record.GetFloat("chapter_count"), 0),
		TranslatedCount:         asInt(record.GetFloat("translated_count"), 0),
		CompletedCount:          asInt(record.GetFloat("completed_count"), 0),
		OriginalCharCount:       asInt(record.GetFloat("original_char_count"), 0),
		TranslatedCharCount:     asInt(record.GetFloat("translated_char_count"), 0),
		RefinedCharCount:        asInt(record.GetFloat("refined_char_count"), 0),
		TotalCharCount:          asInt(record.GetFloat("total_char_count"), 0),
		MaxChapterOrder:         asInt(record.GetFloat("max_chapter_order"), 0),
		CreatedAt:               record.GetString("created"),
		UpdatedAt:               record.GetString("updated"),
	}
}

func chapterFromRecord(record *core.Record) Chapter {
	return Chapter{
		ID:                record.Id,
		NovelID:           record.GetString("novel"),
		ChapterOrder:      asInt(record.GetFloat("chapter_order"), 0),
		Title:             record.GetString("title"),
		TranslatedTitle:   record.GetString("translated_title"),
		OriginalContent:   record.GetString("original_content"),
		TranslatedContent: record.GetString("translated_content"),
		RefinedContent:    record.GetString("refined_content"),
		Status:            defaultString(record.GetString("status"), "pending"),
		ErrorMessage:      record.GetString("error_message"),
		CreatedAt:         record.GetString("created"),
		UpdatedAt:         record.GetString("updated"),
	}
}

func jobFromRecord(record *core.Record) Job {
	return Job{
		ID:                        record.Id,
		OwnerID:                   record.GetString("owner"),
		NovelID:                   record.GetString("novel"),
		Status:                    defaultString(record.GetString("status"), "pending"),
		Operation:                 defaultString(record.GetString("operation"), "translate"),
		Provider:                  record.GetString("provider"),
		Model:                     record.GetString("model"),
		ChapterIDs:                defaultString(record.GetString("chapter_ids"), "[]"),
		OptionsJSON:               defaultString(record.GetString("options_json"), "{}"),
		ErrorMessage:              record.GetString("error_message"),
		TotalChapters:             asInt(record.GetFloat("total_chapters"), 0),
		CompletedChapters:         asInt(record.GetFloat("completed_chapters"), 0),
		FailedChapters:            asInt(record.GetFloat("failed_chapters"), 0),
		AutoSegmentEnabled:        record.GetBool("auto_segment_enabled"),
		AutoSegmentActive:         record.GetBool("auto_segment_active"),
		AutoSegmentCount:          asInt(record.GetFloat("auto_segment_count"), 0),
		AutoSegmentCurrentIndex:   asInt(record.GetFloat("auto_segment_current_index"), 0),
		AutoSegmentCompletedCount: asInt(record.GetFloat("auto_segment_completed_count"), 0),
		AutoSegmentChapterID:      record.GetString("auto_segment_chapter_id"),
		AutoSegmentChapterTitle:   record.GetString("auto_segment_chapter_title"),
		CreatedAt:                 record.GetString("created"),
		UpdatedAt:                 record.GetString("updated"),
	}
}

func epubFromRecord(record *core.Record) Epub {
	file := firstString(record.GetStringSlice("file"))
	return Epub{
		ID:            record.Id,
		NovelID:       record.GetString("novel"),
		FileKind:      record.GetString("file_kind"),
		SourceVariant: record.GetString("source_variant"),
		Label:         record.GetString("label"),
		FileName:      file,
		URL:           "/api/epubs/" + record.Id + "/download",
		CreatedAt:     record.GetString("created"),
		UpdatedAt:     record.GetString("updated"),
	}
}

func readingProgressFromRecord(record *core.Record) ReadingProgress {
	return ReadingProgress{
		ID:            record.Id,
		UserID:        record.GetString("user"),
		NovelID:       record.GetString("novel"),
		ChapterID:     record.GetString("chapter_id"),
		ScrollPercent: record.GetFloat("scroll_percent"),
		CreatedAt:     record.GetString("created"),
		UpdatedAt:     record.GetString("updated"),
	}
}

func applyNovelToRecord(record *core.Record, novel *Novel) {
	record.Set("source_language", novel.SourceLanguage)
	record.Set("target_language", novel.TargetLanguage)
	record.Set("source_title", novel.SourceTitle)
	record.Set("source_author", novel.SourceAuthor)
	record.Set("source_description", novel.SourceDescription)
	record.Set("source_series", novel.SourceSeries)
	record.Set("source_number", novel.SourceNumber)
	record.Set("target_title", novel.TargetTitle)
	record.Set("target_author", novel.TargetAuthor)
	record.Set("target_description", novel.TargetDescription)
	record.Set("target_series", novel.TargetSeries)
	record.Set("target_number", novel.TargetNumber)
	record.Set("glossary", defaultString(novel.Glossary, "[]"))
	record.Set("translation_system_prompt", novel.TranslationSystemPrompt)
	record.Set("translation_user_prompt", novel.TranslationUserPrompt)
	record.Set("refine_system_prompt", novel.RefineSystemPrompt)
	record.Set("refine_user_prompt", novel.RefineUserPrompt)
	record.Set("check_system_prompt", novel.CheckSystemPrompt)
	record.Set("check_user_prompt", novel.CheckUserPrompt)
	record.Set("notes", novel.Notes)
	record.Set("ai_options", defaultString(novel.AIOptions, "{}"))
	record.Set("translation_options", defaultString(novel.TranslationOptions, "{}"))
	record.Set("cleanup_rules", defaultString(novel.CleanupRules, "[]"))
	record.Set("url", novel.URL)
	record.Set("custom_commands", novel.CustomCommands)
	record.Set("status", normalizeNovelStatus(novel.Status))
	record.Set("tags", jsonString(parseNovelTagsJSON(novel.Tags), "[]"))
	record.Set("is_public", novel.IsPublic)
	record.Set("chapter_count", novel.ChapterCount)
	record.Set("translated_count", novel.TranslatedCount)
	record.Set("completed_count", novel.CompletedCount)
	record.Set("original_char_count", novel.OriginalCharCount)
	record.Set("translated_char_count", novel.TranslatedCharCount)
	record.Set("refined_char_count", novel.RefinedCharCount)
	record.Set("total_char_count", novel.TotalCharCount)
	record.Set("max_chapter_order", novel.MaxChapterOrder)
}
