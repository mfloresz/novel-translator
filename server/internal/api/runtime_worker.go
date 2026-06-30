package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	"translator-server/internal/noveldownloader"
	"translator-server/internal/store"
)

func (s *Server) startJobWorker() {
	s.downloadQueue = make(chan string, 128)
	s.translateQueue = make(chan string, 128)

	go s.downloadWorkerLoop()
	go s.translateWorkerLoop()

	jobs, err := s.Store.ListRunnableJobs()
	if err != nil {
		slog.Error("list runnable jobs", "error", err)
		return
	}
	for _, job := range jobs {
		s.enqueueJob(job.ID)
	}
}

func (s *Server) enqueueJob(jobID string) {
	if jobID == "" {
		return
	}
	s.queueMu.Lock()
	if s.queuedJobs == nil {
		s.queuedJobs = map[string]struct{}{}
	}
	if _, exists := s.queuedJobs[jobID]; exists {
		s.queueMu.Unlock()
		return
	}
	s.queuedJobs[jobID] = struct{}{}
	s.queueMu.Unlock()

	job, err := s.Store.GetJob(jobID)
	if err != nil {
		slog.Error("enqueue job: get job", "jobId", jobID, "error", err)
		return
	}

	var queue chan string
	switch job.Operation {
	case "download":
		queue = s.downloadQueue
	default:
		queue = s.translateQueue
	}

	select {
	case queue <- jobID:
	default:
		s.queueMu.Lock()
		delete(s.queuedJobs, jobID)
		s.queueMu.Unlock()
		msg := "Server is busy processing other jobs. Please wait a few minutes and try again."
		if ue := s.Store.UpdateJob(jobID, map[string]any{
			"status":       "failed",
			"errorMessage": msg,
		}); ue != nil {
			slog.Error("update job status on queue saturation", "jobId", jobID, "error", ue)
		}
		slog.Warn("job queue full, job rejected",
			"jobId", jobID,
			"queueLen", len(queue),
			"queueCap", cap(queue))
	}
}

func (s *Server) workerLoop(queue chan string) {
	for jobID := range queue {
		s.queueMu.Lock()
		delete(s.queuedJobs, jobID)
		s.queueMu.Unlock()
		if err := s.processJob(jobID); err != nil {
			slog.Error("job failed", "jobId", jobID, "error", err)
		}
	}
}

func (s *Server) downloadWorkerLoop() {
	s.workerLoop(s.downloadQueue)
}

func (s *Server) translateWorkerLoop() {
	s.workerLoop(s.translateQueue)
}

func (s *Server) processJob(jobID string) error {
	job, err := s.Store.GetJob(jobID)
	if err != nil {
		return fmt.Errorf("get job: %w", err)
	}
	if job.Status == "cancelled" || job.Status == "done" || job.Status == "failed" {
		return nil
	}

	runCtx, cancel := context.WithCancel(context.Background())
	s.registerJobCancel(jobID, cancel)
	defer func() {
		cancel()
		s.unregisterJobCancel(jobID)
	}()

	if job.Operation == "download" {
		return s.processDownloadJob(runCtx, job)
	}

	jc, err := s.buildJobContext(runCtx, job)
	if err != nil {
		if ue := s.Store.UpdateJob(jobID, map[string]interface{}{"status": "failed", "errorMessage": err.Error()}); ue != nil {
			slog.Error("update job status on build context failure", "jobId", jobID, "error", ue)
		}
		return fmt.Errorf("load job context: %w", err)
	}
	if len(jc.chapters) == 0 {
		err := fmt.Errorf("job %s has no chapters to process", jobID)
		if ue := s.Store.UpdateJob(jobID, map[string]interface{}{"status": "failed", "errorMessage": err.Error()}); ue != nil {
			slog.Error("update job status on empty chapters", "jobId", jobID, "error", ue)
		}
		return err
	}

	if err := s.Store.UpdateJob(jobID, map[string]interface{}{
		"status":                  "running",
		"operation":               job.Operation,
		"provider":                jc.cfg.AI.Provider,
		"model":                   effectiveModel(jc.cfg.AI),
		"errorMessage":            "",
		"totalChapters":           len(jc.chapters),
		"autoSegmentEnabled":      jc.cfg.Translation.AutoSegment,
		"autoSegmentActive":       false,
		"autoSegmentCount":        0,
		"autoSegmentChapterId":    "",
		"autoSegmentChapterTitle": "",
	}); err != nil {
		return fmt.Errorf("set job running: %w", err)
	}

	var wasCancelled bool
	for idx := range jc.chapters {
		if runCtx.Err() != nil {
			wasCancelled = true
			break
		}
		chapter := jc.chapters[idx]
		jc.resetSegmentProgress()

		var chapterErr error
		switch job.Operation {
		case "refine":
			chapterErr = s.runRefineChapter(jc, idx, &chapter)
		default:
			segmentation := previewChapterSegmentation(jc.cfg, chapter)
			jc.recordSegProgress(0, 0, segmentation.SegmentCount, chapter.ID, chapter.Title, segmentation.Applied)
			jc.flushProgress(s)
			var segErr error
			_, segErr = s.runTranslateChapterDetailed(jc, idx, &chapter)
			chapterErr = segErr
		}

		if runCtx.Err() != nil {
			wasCancelled = true
		}

		jc.recordChapterResult(chapterErr)
		if chapterErr != nil {
			if wasCancelled {
				if err := s.Store.UpdateChapterStatusFast(chapter.ID, "pending", ""); err != nil {
					slog.Warn("reset chapter status on cancel", "chapterId", chapter.ID, "error", err)
				}
			} else {
				if err := s.Store.UpdateChapterStatusFast(chapter.ID, "failed", chapterErr.Error()); err != nil {
					slog.Warn("update chapter status on failure", "chapterId", chapter.ID, "error", err)
				}
			}
		}
		jc.resetSegmentProgress()
		jc.flushProgress(s)
	}

	if jc.statsDirty {
		if err := s.Store.RecalculateNovelStats(jc.novel.ID); err != nil {
			slog.Error("recalculate novel stats at job end", "jobId", jobID, "error", err)
		}
	}

	finalStatus := "done"
	finalError := ""
	if wasCancelled {
		finalStatus = "cancelled"
	} else if jc.failed > 0 {
		finalStatus = "failed"
		finalError = jc.lastError
	}

	return s.Store.UpdateJob(jobID, map[string]interface{}{
		"status":                    finalStatus,
		"completedChapters":         jc.completed,
		"failedChapters":            jc.failed,
		"errorMessage":              finalError,
		"autoSegmentActive":         false,
		"autoSegmentCurrentIndex":   0,
		"autoSegmentCompletedCount": 0,
		"autoSegmentChapterId":      "",
		"autoSegmentChapterTitle":   "",
	})
}

type downloadJobOptions struct {
	URL            string                      `json:"url"`
	Chapters       []store.DownloadChapterInfo `json:"chapters"`
	StartOrder     int                         `json:"startOrder"`
	SourceLanguage string                      `json:"sourceLanguage"`
	TargetLanguage string                      `json:"targetLanguage"`
}

func (s *Server) processDownloadJob(ctx context.Context, job *store.Job) error {
	var opts downloadJobOptions
	if err := json.Unmarshal([]byte(job.OptionsJSON), &opts); err != nil {
		if ue := s.Store.UpdateJob(job.ID, map[string]interface{}{"status": "failed", "errorMessage": fmt.Sprintf("invalid job options: %v", err)}); ue != nil {
			slog.Error("update job status on invalid options", "jobId", job.ID, "error", ue)
		}
		return fmt.Errorf("parse download options: %w", err)
	}
	dl := s.DownloaderFactory()
	if len(opts.Chapters) == 0 {
		if ue := s.Store.UpdateJob(job.ID, map[string]interface{}{"status": "done"}); ue != nil {
			slog.Error("update job status on no chapters", "jobId", job.ID, "error", ue)
		}
		if ctx.Err() == nil {
			if err := dl.SleepBetweenChapters(ctx); err != nil {
				return err
			}
		}
		return nil
	}
	if err := s.Store.UpdateJob(job.ID, map[string]interface{}{
		"status":        "running",
		"totalChapters": len(opts.Chapters),
		"errorMessage":  "",
	}); err != nil {
		return fmt.Errorf("set job running: %w", err)
	}
	parser := dl.FindParser(opts.URL)
	if parser == nil {
		if ue := s.Store.UpdateJob(job.ID, map[string]interface{}{"status": "failed", "errorMessage": "unsupported URL"}); ue != nil {
			slog.Error("update job status on unsupported URL", "jobId", job.ID, "error", ue)
		}
		return fmt.Errorf("unsupported URL: %s", opts.URL)
	}
	completed := 0
	failed := 0
	for idx, chInfo := range opts.Chapters {
		if err := ctx.Err(); err != nil {
			return nil
		}
		if idx > 0 {
			if err := dl.SleepBetweenChapters(ctx); err != nil {
				return err
			}
		}
		chURLs := []noveldownloader.ChapterURL{{URL: chInfo.URL, Title: chInfo.Title}}
		downloaded, err := dl.DownloadChapters(ctx, chURLs, 1, 1)
		if err != nil {
			if ctxErr := ctx.Err(); ctxErr != nil {
				return nil
			}
			failed++
			slog.Error("failed to download chapter", "jobId", job.ID, "chapter", chInfo.Title, "error", err)
		} else if len(downloaded) > 0 {
			ch := downloaded[0]
			chTitle := ch.Title
			if chTitle == "" {
				chTitle = chInfo.Title
			}
			if chTitle == "" {
				chTitle = fmt.Sprintf("Capítulo %d", opts.StartOrder+idx)
			}
			if _, err := s.Store.UpsertChapterWithoutStats(job.OwnerID, job.NovelID, &store.Chapter{
				ChapterOrder:    opts.StartOrder + idx,
				Title:           chTitle,
				OriginalContent: ch.Markdown,
				Status:          "pending",
			}); err != nil {
				failed++
				slog.Error("failed to save chapter", "jobId", job.ID, "chapter", chTitle, "error", err)
			} else {
				completed++
			}
		} else {
			failed++
			slog.Warn("empty download result", "jobId", job.ID, "chapter", chInfo.Title)
		}
		if ue := s.Store.UpdateJob(job.ID, map[string]interface{}{
			"completedChapters": completed,
			"failedChapters":    failed,
		}); ue != nil {
			slog.Warn("update job progress", "jobId", job.ID, "error", ue)
		}
	}
	if err := s.Store.RecalculateNovelStats(job.NovelID); err != nil {
		slog.Error("failed to recalculate novel stats after download", "jobId", job.ID, "error", err)
	}
	status := "done"
	if failed > 0 {
		status = "failed"
	}
	if ctx.Err() == nil {
		if err := dl.SleepBetweenChapters(ctx); err != nil {
			return err
		}
	}
	return s.Store.UpdateJob(job.ID, map[string]interface{}{
		"status":            status,
		"completedChapters": completed,
		"failedChapters":    failed,
	})
}
