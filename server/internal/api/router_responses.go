package api

import (
	"encoding/json"
	"strings"

	"translator-server/internal/store"
)

func parseJSONFields(n *store.Novel) map[string]any {
	m := map[string]any{
		"id": n.ID, "ownerId": n.OwnerID,
		"sourceLanguage": n.SourceLanguage, "targetLanguage": n.TargetLanguage,
		"sourceTitle": n.SourceTitle, "sourceAuthor": n.SourceAuthor, "sourceDescription": n.SourceDescription,
		"sourceSeries": n.SourceSeries, "sourceNumber": n.SourceNumber,
		"targetTitle": n.TargetTitle, "targetAuthor": n.TargetAuthor, "targetDescription": n.TargetDescription,
		"targetSeries": n.TargetSeries, "targetNumber": n.TargetNumber,
		"url": n.URL, "customCommands": n.CustomCommands, "status": n.Status, "coverPath": n.CoverPath,
		"isPublic":     n.IsPublic,
		"chapterCount": n.ChapterCount, "translatedCount": n.TranslatedCount, "completedCount": n.CompletedCount,
		"originalCharCount": n.OriginalCharCount, "translatedCharCount": n.TranslatedCharCount,
		"refinedCharCount": n.RefinedCharCount, "totalCharCount": n.TotalCharCount,
		"maxChapterOrder": n.MaxChapterOrder,
		"createdAt":       n.CreatedAt, "updatedAt": n.UpdatedAt,
	}
	var gl, tags, aio, tro, cr any
	_ = json.Unmarshal([]byte(n.Glossary), &gl)
	_ = json.Unmarshal([]byte(n.Tags), &tags)
	_ = json.Unmarshal([]byte(n.AIOptions), &aio)
	_ = json.Unmarshal([]byte(n.TranslationOptions), &tro)
	_ = json.Unmarshal([]byte(n.CleanupRules), &cr)
	m["glossary"] = gl
	m["tags"] = tags
	m["prompts"] = store.BuildNovelPromptOverridesMap(n)
	m["aiOptions"] = aio
	m["translationOptions"] = tro
	m["cleanupRules"] = cr
	m["notes"] = n.Notes
	return m
}

func parseJSONFieldsSubset(n *store.Novel, fields []string) map[string]any {
	m := make(map[string]any, len(fields))
	for _, f := range fields {
		f = strings.TrimSpace(f)
		switch f {
		case "id":
			m["id"] = n.ID
		case "ownerId":
			m["ownerId"] = n.OwnerID
		case "sourceLanguage":
			m["sourceLanguage"] = n.SourceLanguage
		case "targetLanguage":
			m["targetLanguage"] = n.TargetLanguage
		case "sourceTitle":
			m["sourceTitle"] = n.SourceTitle
		case "sourceAuthor":
			m["sourceAuthor"] = n.SourceAuthor
		case "sourceDescription":
			m["sourceDescription"] = n.SourceDescription
		case "sourceSeries":
			m["sourceSeries"] = n.SourceSeries
		case "sourceNumber":
			m["sourceNumber"] = n.SourceNumber
		case "targetTitle":
			m["targetTitle"] = n.TargetTitle
		case "targetAuthor":
			m["targetAuthor"] = n.TargetAuthor
		case "targetDescription":
			m["targetDescription"] = n.TargetDescription
		case "targetSeries":
			m["targetSeries"] = n.TargetSeries
		case "targetNumber":
			m["targetNumber"] = n.TargetNumber
		case "url":
			m["url"] = n.URL
		case "customCommands":
			m["customCommands"] = n.CustomCommands
		case "status":
			m["status"] = n.Status
		case "coverPath":
			m["coverPath"] = n.CoverPath
		case "isPublic":
			m["isPublic"] = n.IsPublic
		case "chapterCount":
			m["chapterCount"] = n.ChapterCount
		case "translatedCount":
			m["translatedCount"] = n.TranslatedCount
		case "completedCount":
			m["completedCount"] = n.CompletedCount
		case "originalCharCount":
			m["originalCharCount"] = n.OriginalCharCount
		case "translatedCharCount":
			m["translatedCharCount"] = n.TranslatedCharCount
		case "refinedCharCount":
			m["refinedCharCount"] = n.RefinedCharCount
		case "totalCharCount":
			m["totalCharCount"] = n.TotalCharCount
		case "maxChapterOrder":
			m["maxChapterOrder"] = n.MaxChapterOrder
		case "createdAt":
			m["createdAt"] = n.CreatedAt
		case "updatedAt":
			m["updatedAt"] = n.UpdatedAt
		case "glossary":
			var v any
			_ = json.Unmarshal([]byte(n.Glossary), &v)
			m["glossary"] = v
		case "tags":
			var v any
			_ = json.Unmarshal([]byte(n.Tags), &v)
			m["tags"] = v
		case "prompts":
			m["prompts"] = store.BuildNovelPromptOverridesMap(n)
		case "aiOptions":
			var v any
			_ = json.Unmarshal([]byte(n.AIOptions), &v)
			m["aiOptions"] = v
		case "translationOptions":
			var v any
			_ = json.Unmarshal([]byte(n.TranslationOptions), &v)
			m["translationOptions"] = v
		case "cleanupRules":
			var v any
			_ = json.Unmarshal([]byte(n.CleanupRules), &v)
			m["cleanupRules"] = v
		case "notes":
			m["notes"] = n.Notes
		}
	}
	return m
}

func promptToResponse(p store.Prompt) map[string]any {
	return map[string]any{
		"id":          p.Key,
		"key":         p.Key,
		"label":       p.Label,
		"description": p.Description,
		"prompt": map[string]any{
			"systemPrompt": p.SystemPrompt,
			"userPrompt":   p.UserPrompt,
		},
		"active":    p.Active == 1,
		"updatedAt": p.UpdatedAt,
	}
}

func promptsToResponse(items []store.Prompt) []map[string]any {
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		out = append(out, promptToResponse(item))
	}
	return out
}

func chapterRecord(c store.Chapter) map[string]any {
	return map[string]any{
		"id":                c.ID,
		"novelId":           c.NovelID,
		"chapterOrder":      c.ChapterOrder,
		"title":             c.Title,
		"translatedTitle":   c.TranslatedTitle,
		"originalContent":   c.OriginalContent,
		"translatedContent": c.TranslatedContent,
		"refinedContent":    c.RefinedContent,
		"status":            c.Status,
		"errorMessage":      c.ErrorMessage,
		"createdAt":         c.CreatedAt,
		"updatedAt":         c.UpdatedAt,
	}
}

func chapterSummaryRecord(c store.ChapterSummary) map[string]any {
	return map[string]any{
		"id":                   c.ID,
		"novelId":              c.NovelID,
		"chapterOrder":         c.ChapterOrder,
		"title":                c.Title,
		"translatedTitle":      c.TranslatedTitle,
		"status":               c.Status,
		"errorMessage":         c.ErrorMessage,
		"hasOriginalContent":   c.HasOriginalContent,
		"hasTranslatedContent": c.HasTranslatedContent,
		"hasRefinedContent":    c.HasRefinedContent,
		"originalChars":        c.OriginalChars,
		"translatedChars":      c.TranslatedChars,
		"refinedChars":         c.RefinedChars,
		"createdAt":            c.CreatedAt,
		"updatedAt":            c.UpdatedAt,
	}
}

func chapterStatsRecord(s *store.ChapterStats) map[string]any {
	if s == nil {
		return map[string]any{
			"totalChapters":        0,
			"completedChapters":    0,
			"translatedChapters":   0,
			"originalCharacters":   0,
			"translatedCharacters": 0,
			"refinedCharacters":    0,
			"totalCharacters":      0,
			"maxChapterOrder":      0,
		}
	}
	return map[string]any{
		"totalChapters":        s.TotalChapters,
		"completedChapters":    s.CompletedChapters,
		"translatedChapters":   s.TranslatedChapters,
		"originalCharacters":   s.OriginalCharacters,
		"translatedCharacters": s.TranslatedCharacters,
		"refinedCharacters":    s.RefinedCharacters,
		"totalCharacters":      s.TotalCharacters,
		"maxChapterOrder":      s.MaxChapterOrder,
	}
}

func jobRecord(j store.Job) map[string]any {
	chapterIDs := []string{}
	if trimmed := strings.TrimSpace(j.ChapterIDs); trimmed != "" {
		if err := json.Unmarshal([]byte(trimmed), &chapterIDs); err != nil {
			chapterIDs = []string{}
		}
	}
	return map[string]any{
		"id":                        j.ID,
		"novelId":                   j.NovelID,
		"status":                    j.Status,
		"operation":                 j.Operation,
		"provider":                  j.Provider,
		"model":                     j.Model,
		"totalChapters":             j.TotalChapters,
		"completedChapters":         j.CompletedChapters,
		"failedChapters":            j.FailedChapters,
		"errorMessage":              j.ErrorMessage,
		"createdAt":                 j.CreatedAt,
		"updatedAt":                 j.UpdatedAt,
		"novelTitle":                j.NovelTitle,
		"chapterIds":                chapterIDs,
		"autoSegmentEnabled":        j.AutoSegmentEnabled,
		"autoSegmentActive":         j.AutoSegmentActive,
		"autoSegmentCount":          j.AutoSegmentCount,
		"autoSegmentCurrentIndex":   j.AutoSegmentCurrentIndex,
		"autoSegmentCompletedCount": j.AutoSegmentCompletedCount,
		"autoSegmentChapterId":      j.AutoSegmentChapterID,
		"autoSegmentChapterTitle":   j.AutoSegmentChapterTitle,
	}
}

func readingProgressRecord(rp store.ReadingProgress) map[string]any {
	return map[string]any{
		"id":            rp.ID,
		"userId":        rp.UserID,
		"novelId":       rp.NovelID,
		"chapterId":     rp.ChapterID,
		"scrollPercent": rp.ScrollPercent,
		"createdAt":     rp.CreatedAt,
		"updatedAt":     rp.UpdatedAt,
	}
}

func epubRecord(e store.Epub) map[string]any {
	return map[string]any{
		"id":            e.ID,
		"novelId":       e.NovelID,
		"fileKind":      e.FileKind,
		"sourceVariant": e.SourceVariant,
		"label":         e.Label,
		"fileName":      e.FileName,
		"url":           e.URL,
		"createdAt":     e.CreatedAt,
		"updatedAt":     e.UpdatedAt,
	}
}
