package api

import (
	"fmt"
	"log/slog"
	"strings"

	"translator-server/internal/ai"
	"translator-server/internal/store"
)

func (s *Server) runRefineChapter(jc *jobContext, idx int, chapter *store.Chapter) error {
	if strings.TrimSpace(chapter.TranslatedContent) == "" {
		return fmt.Errorf("chapter %s has no translated content", chapter.ID)
	}
	current := chapter.TranslatedContent
	// At least one refine pass. With check enabled, run up to MaxRetries
	// refine-check cycles; each iteration either passes the check (exits early)
	// or retries with a refined version.
	attempts := 1
	if jc.cfg.Translation.EnableCheck {
		attempts = max(1, jc.cfg.Translation.MaxRetries)
	}
	prevOrig, prevTranslated := "", ""
	if jc.cfg.IncludePrevTitle && idx > 0 {
		prevOrig = jc.chapters[idx-1].Title
		prevTranslated = jc.chapters[idx-1].TranslatedTitle
	}
	for attempt := 1; attempt <= attempts; attempt++ {
		if jc.cfg.Translation.EnableCheck {
			checkPrompt := buildCheckPrompt(jc.cfg, jc.novel, chapter, prevOrig, prevTranslated, current)
			checkOut, err := jc.provider.Check(jc.runCtx, checkPrompt)
			if err == nil && checkOut.OK {
				chapter.RefinedContent = current
				chapter.Status = "refined"
				chapter.ErrorMessage = ""
				if err := s.Store.SaveChapterTranslationFast(chapter.ID, "", "", chapter.RefinedContent, "refined"); err != nil {
					return fmt.Errorf("save chapter refinement: %w", err)
				}
				jc.statsDirty = true
				return nil
			}
		}
		chunks := buildRefineChunks(chapter.OriginalContent, current, 15, 2)
		partials := make([]string, 0, len(chunks))
		for _, chunk := range chunks {
			if err := jc.runCtx.Err(); err != nil {
				return fmt.Errorf("refine context cancelled: %w", err)
			}
			refined, err := jc.provider.Refine(jc.runCtx, ai.RefineInput{
				OriginalText:   chunk.OriginalChunk,
				TranslatedText: buildRefinePrompt(jc.cfg, jc.novel, chapter, chunk),
				SourceLanguage: jc.novel.SourceLanguage,
				TargetLanguage: jc.novel.TargetLanguage,
			})
			if err != nil {
				return fmt.Errorf("refine chapter chunk: %w", err)
			}
			updatedChunk, applied := applyRefineEdits(chunk.TranslationChunk, refined.Edits)
			if len(refined.Edits) > 0 && applied == 0 {
				slog.Warn("refine edits skipped", "chapterId", chapter.ID, "chunk", chunk.Index, "edits", len(refined.Edits))
			}
			partials = append(partials, updatedChunk)
		}
		current = strings.Join(partials, "\n")
	}
	chapter.RefinedContent = current
	chapter.Status = "refined"
	chapter.ErrorMessage = ""
	if err := s.Store.SaveChapterTranslationFast(chapter.ID, "", "", chapter.RefinedContent, "refined"); err != nil {
		return fmt.Errorf("save chapter refinement: %w", err)
	}
	jc.statsDirty = true
	return nil
}

func buildRefinePrompt(cfg resolvedJobConfig, novel *store.Novel, chapter *store.Chapter, chunk refineChunk) string {
	glossaryText := formatGlossary(cfg.Glossary)
	values := map[string]string{
		"{SOURCE_LANG}":         novel.SourceLanguage,
		"{TARGET_LANG}":         novel.TargetLanguage,
		"{GLOSSARY}":            glossaryText,
		"{ORIGINAL}":            chunk.OriginalContext,
		"{TRANSLATION}":         chunk.TranslationContext,
		"{ORIGINAL_CHUNK}":      chunk.OriginalChunk,
		"{TRANSLATION_CHUNK}":   chunk.TranslationChunk,
		"{TRANSLATION_CONTEXT}": chunk.TranslationContext,
		"{START_LINE}":          fmt.Sprintf("%d", chunk.StartLine+1),
		"{END_LINE}":            fmt.Sprintf("%d", chunk.EndLine),
	}
	systemPrompt := fillPrompt(cfg.Prompts.Refine.SystemPrompt, values)
	userPrompt := fillPrompt(cfg.Prompts.Refine.UserPrompt, values)
	return strings.TrimSpace(strings.Join([]string{systemPrompt, userPrompt}, "\n\n"))
}

func buildRefineChunks(original, translation string, chunkSize, overlap int) []refineChunk {
	if chunkSize <= 0 {
		chunkSize = 15
	}
	if overlap < 0 {
		overlap = 0
	}
	originalLines := splitLines(original)
	translationLines := splitLines(translation)
	if len(translationLines) == 0 {
		return nil
	}
	chunks := make([]refineChunk, 0, (len(translationLines)+chunkSize-1)/chunkSize)
	for start := 0; start < len(translationLines); start += chunkSize {
		end := min(start+chunkSize, len(translationLines))
		contextStart := max(0, start-overlap)
		contextEnd := min(end+overlap, len(translationLines))
		originalContextStart := min(contextStart, len(originalLines))
		originalContextEnd := min(contextEnd, len(originalLines))
		originalChunkStart := min(start, len(originalLines))
		originalChunkEnd := min(end, len(originalLines))
		chunks = append(chunks, refineChunk{
			Index:              len(chunks),
			StartLine:          start,
			EndLine:            end,
			OriginalContext:    strings.Join(originalLines[originalContextStart:originalContextEnd], "\n"),
			OriginalChunk:      strings.Join(originalLines[originalChunkStart:originalChunkEnd], "\n"),
			TranslationContext: strings.Join(translationLines[contextStart:contextEnd], "\n"),
			TranslationChunk:   strings.Join(translationLines[start:end], "\n"),
		})
	}
	return chunks
}

func splitLines(text string) []string {
	text = strings.ReplaceAll(text, "\r\n", "\n")
	text = strings.ReplaceAll(text, "\r", "\n")
	return strings.Split(text, "\n")
}

func applyRefineEdits(text string, edits []ai.RefineEdit) (string, int) {
	applied := 0
	for _, edit := range edits {
		original := trimEditBoundaryNewlines(edit.Original)
		replacement := trimEditBoundaryNewlines(edit.Replacement)
		if original == "" || original == replacement {
			continue
		}
		if strings.Count(text, original) != 1 {
			continue
		}
		text = strings.Replace(text, original, replacement, 1)
		applied++
	}
	return text, applied
}

func trimEditBoundaryNewlines(text string) string {
	return strings.Trim(text, "\r\n")
}

func buildCheckPrompt(cfg resolvedJobConfig, novel *store.Novel, chapter *store.Chapter, prevOrig, prevTranslated, current string) ai.CheckInput {
	systemPrompt := fillPrompt(cfg.Prompts.Check.SystemPrompt, map[string]string{
		"{SOURCE_LANG}": novel.SourceLanguage,
		"{TARGET_LANG}": novel.TargetLanguage,
		"{ORIGINAL}":    chapter.OriginalContent,
		"{TRANSLATION}": current,
	})
	userPrompt := fillPrompt(cfg.Prompts.Check.UserPrompt, map[string]string{
		"{SOURCE_LANG}": novel.SourceLanguage,
		"{TARGET_LANG}": novel.TargetLanguage,
		"{ORIGINAL}":    chapter.OriginalContent,
		"{TRANSLATION}": current,
	})
	return ai.CheckInput{
		SystemPrompt:       strings.TrimSpace(strings.Join([]string{systemPrompt, userPrompt}, "\n\nAdditional review instructions:\n")),
		TitleOriginal:      chapter.Title,
		TitleTranslated:    chapter.TranslatedTitle,
		ContentOriginal:    chapter.OriginalContent,
		ContentTranslated:  current,
		PreviousTitleOrig:  prevOrig,
		PreviousTitleTrans: prevTranslated,
		SourceLanguage:     novel.SourceLanguage,
		TargetLanguage:     novel.TargetLanguage,
	}
}
