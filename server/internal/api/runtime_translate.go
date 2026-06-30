package api

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"translator-server/internal/ai"
	"translator-server/internal/store"
)

type jobContext struct {
	jobID             string
	runCtx            context.Context
	novel             *store.Novel
	chapters          []store.Chapter
	cfg               resolvedJobConfig
	provider          ai.Provider
	glossaryText      string
	baseSystemPrompt  string
	statsDirty        bool
	pendingSegIndex   int
	pendingSegDone    int
	pendingSegTotal   int
	pendingSegActive  bool
	pendingSegChapter string
	pendingSegTitle   string
	dirty             bool
	completed         int
	failed            int
	lastError         string
}

func (s *Server) buildJobContext(ctx context.Context, job *store.Job) (*jobContext, error) {
	chapters, novel, err := s.Store.LoadJobChapters(job)
	if err != nil {
		return nil, fmt.Errorf("load job chapters: %w", err)
	}
	cfg, err := s.resolveJobConfig(novel, job)
	if err != nil {
		return nil, fmt.Errorf("resolve job config: %w", err)
	}
	provider, err := s.newAIProvider(cfg.AI)
	if err != nil {
		return nil, fmt.Errorf("new AI provider: %w", err)
	}
	glossaryText := formatGlossary(cfg.Glossary)
	baseValues := map[string]string{
		"{SOURCE_LANG}": novel.SourceLanguage,
		"{TARGET_LANG}": novel.TargetLanguage,
		"{GLOSSARY}":    glossaryText,
		"{TEXT}":        "",
	}
	baseSystemPrompt := strings.TrimSpace(fillPrompt(cfg.Prompts.Translation.SystemPrompt, baseValues))
	return &jobContext{
		jobID:            job.ID,
		runCtx:           ctx,
		novel:            novel,
		chapters:         chapters,
		cfg:              cfg,
		provider:         provider,
		glossaryText:     glossaryText,
		baseSystemPrompt: baseSystemPrompt,
	}, nil
}

func (jc *jobContext) markDirty() {
	jc.dirty = true
}

func (jc *jobContext) flushProgress(s *Server) {
	if !jc.dirty {
		return
	}
	patch := map[string]interface{}{
		"completedChapters":         jc.completed,
		"failedChapters":            jc.failed,
		"errorMessage":              jc.lastError,
		"autoSegmentActive":         jc.pendingSegActive,
		"autoSegmentCount":          jc.pendingSegTotal,
		"autoSegmentCurrentIndex":   jc.pendingSegIndex,
		"autoSegmentCompletedCount": jc.pendingSegDone,
		"autoSegmentChapterId":      jc.pendingSegChapter,
		"autoSegmentChapterTitle":   jc.pendingSegTitle,
	}
	if err := s.Store.UpdateJob(jc.jobID, patch); err != nil {
		slog.Warn("flush job progress", "jobId", jc.jobID, "error", err)
	}
	jc.dirty = false
}

func (jc *jobContext) recordSegProgress(segIndex, segDone, segTotal int, chapterID, chapterTitle string, active bool) {
	jc.pendingSegIndex = segIndex
	jc.pendingSegDone = segDone
	jc.pendingSegTotal = segTotal
	jc.pendingSegChapter = chapterID
	jc.pendingSegTitle = chapterTitle
	jc.pendingSegActive = active
	jc.markDirty()
}

func (jc *jobContext) recordChapterResult(err error) {
	if err != nil {
		jc.failed++
		jc.lastError = err.Error()
	} else {
		jc.completed++
	}
	jc.markDirty()
}

func (jc *jobContext) resetSegmentProgress() {
	jc.pendingSegActive = false
	jc.pendingSegIndex = 0
	jc.pendingSegDone = 0
	jc.pendingSegTotal = 0
	jc.markDirty()
}

func previewChapterSegmentation(cfg resolvedJobConfig, chapter store.Chapter) chapterSegmentationStatus {
	if strings.TrimSpace(chapter.OriginalContent) == "" {
		return chapterSegmentationStatus{}
	}
	segments := buildSegments(chapter.OriginalContent, cfg.Translation)
	return chapterSegmentationStatus{Applied: len(segments) > 1, SegmentCount: len(segments)}
}

func (s *Server) runTranslateChapterDetailed(jc *jobContext, idx int, chapter *store.Chapter) (chapterSegmentationStatus, error) {
	if strings.TrimSpace(chapter.OriginalContent) == "" {
		return chapterSegmentationStatus{}, fmt.Errorf("chapter %s has no original content", chapter.ID)
	}
	segments := buildSegments(chapter.OriginalContent, jc.cfg.Translation)
	segmentation := chapterSegmentationStatus{Applied: len(segments) > 1, SegmentCount: len(segments)}
	partials := make([]string, 0, len(segments))
	translatedTitle := strings.TrimSpace(chapter.TranslatedTitle)
	ctx := jc.runCtx
	if translatedTitle == "" {
		var err error
		translatedTitle, err = s.translateChapterTitle(ctx, jc, idx, chapter)
		if err != nil {
			return segmentation, fmt.Errorf("translate title: %w", err)
		}
		chapter.TranslatedTitle = translatedTitle
	}
	for _, seg := range segments {
		if err := ctx.Err(); err != nil {
			return segmentation, fmt.Errorf("translate context cancelled: %w", err)
		}
		jc.recordSegProgress(seg.Index+1, len(partials), len(segments), chapter.ID, chapter.Title, segmentation.Applied)
		translatedText, err := s.translateSegmentText(ctx, jc, seg)
		if err != nil {
			return segmentation, fmt.Errorf("translate segment: %w", err)
		}
		partials = append(partials, strings.TrimSpace(translatedText))
	}
	chapter.TranslatedTitle = translatedTitle
	chapter.TranslatedContent = joinSegments(segments, partials)
	chapter.Status = "translated"
	chapter.ErrorMessage = ""
	if err := s.Store.SaveChapterTranslationFast(chapter.ID, chapter.TranslatedTitle, chapter.TranslatedContent, "", "translated"); err != nil {
		return segmentation, fmt.Errorf("save chapter translation: %w", err)
	}
	jc.statsDirty = true
	return segmentation, nil
}

func (s *Server) translateChapterTitle(ctx context.Context, jc *jobContext, idx int, chapter *store.Chapter) (string, error) {
	previousOriginal := ""
	previousTranslated := ""
	if jc.cfg.IncludePrevTitle && idx > 0 {
		previousOriginal = jc.chapters[idx-1].Title
		previousTranslated = jc.chapters[idx-1].TranslatedTitle
	}
	maxRetries := jc.cfg.Translation.MaxRetries
	if maxRetries < 0 {
		maxRetries = 0
	}
	var lastErr error
	for attempt := 0; attempt <= maxRetries; attempt++ {
		translatedTitle, err := jc.provider.TranslateTitle(ctx, ai.TranslateTitleInput{
			SystemPrompt:       jc.baseSystemPrompt,
			TitleOriginal:      chapter.Title,
			PreviousTitleOrig:  previousOriginal,
			PreviousTitleTrans: previousTranslated,
			SourceLanguage:     jc.novel.SourceLanguage,
			TargetLanguage:     jc.novel.TargetLanguage,
			Options: map[string]string{
				"provider": jc.cfg.AI.Provider,
				"model":    effectiveModel(jc.cfg.AI),
			},
		})
		if err != nil {
			lastErr = err
			if attempt < maxRetries {
				if err := sleepWithContext(ctx, time.Duration(attempt+1)*500*time.Millisecond); err != nil {
					return "", err
				}
			}
			continue
		}
		if err := validateTranslatedTitle(translatedTitle); err != nil {
			lastErr = err
			if attempt < maxRetries {
				if err := sleepWithContext(ctx, time.Duration(attempt+1)*500*time.Millisecond); err != nil {
					return "", err
				}
			}
			continue
		}
		return strings.TrimSpace(translatedTitle), nil
	}
	return "", lastErr
}

func (s *Server) translateSegmentText(ctx context.Context, jc *jobContext, segment chapterSegment) (string, error) {
	maxRetries := jc.cfg.Translation.MaxRetries
	if maxRetries < 0 {
		maxRetries = 0
	}
	var lastErr error
	for attempt := 0; attempt <= maxRetries; attempt++ {
		translatedText, err := jc.provider.TranslateText(ctx, ai.TranslateTextInput{
			SystemPrompt:    jc.baseSystemPrompt,
			TextToTranslate: strings.TrimSpace(segment.Text),
			SourceLanguage:  jc.novel.SourceLanguage,
			TargetLanguage:  jc.novel.TargetLanguage,
			Options: map[string]string{
				"provider": jc.cfg.AI.Provider,
				"model":    effectiveModel(jc.cfg.AI),
			},
		})
		if err != nil {
			lastErr = err
			if attempt < maxRetries {
				if err := sleepWithContext(ctx, time.Duration(attempt+1)*500*time.Millisecond); err != nil {
					return "", err
				}
			}
			continue
		}
		if err := validateTranslatedText(translatedText); err != nil {
			lastErr = err
			if attempt < maxRetries {
				if err := sleepWithContext(ctx, time.Duration(attempt+1)*500*time.Millisecond); err != nil {
					return "", err
				}
			}
			continue
		}
		return strings.TrimSpace(translatedText), nil
	}
	return "", lastErr
}

func validateTranslatedTitle(translatedTitle string) error {
	if strings.TrimSpace(translatedTitle) == "" {
		return fmt.Errorf("model returned empty translated title")
	}
	return nil
}

func validateTranslatedText(translatedText string) error {
	if strings.TrimSpace(translatedText) == "" {
		return fmt.Errorf("model returned empty translated text")
	}
	return nil
}

func joinSegments(segments []chapterSegment, partials []string) string {
	parts := make([]string, 0, len(partials))
	for i := range segments {
		if i < len(partials) && strings.TrimSpace(partials[i]) != "" {
			parts = append(parts, strings.TrimSpace(partials[i]))
		}
	}
	return strings.Join(parts, "\n\n")
}

func sleepWithContext(ctx context.Context, d time.Duration) error {
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(d):
		return nil
	}
}
