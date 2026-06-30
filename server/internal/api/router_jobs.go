package api

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/store"
)

func registerJobRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.POST("/db/novels/{novelId}/translation-jobs", func(e *core.RequestEvent) error {
		body := struct {
			ChapterIDs []string       `json:"chapterIds"`
			Operation  string         `json:"operation"`
			Options    map[string]any `json:"options"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		provider, _ := body.Options["provider"].(string)
		model, _ := body.Options["model"].(string)
		idsJSON, _ := json.Marshal(body.ChapterIDs)
		optionsJSON, _ := json.Marshal(body.Options)
		job := &store.Job{NovelID: e.Request.PathValue("novelId"), Status: "pending", Operation: defaultString(body.Operation, "translate"), Provider: provider, Model: model, ChapterIDs: string(idsJSON), OptionsJSON: string(optionsJSON), TotalChapters: len(body.ChapterIDs)}
		if err := s.Store.CreateJob(e.Auth.Id, job); err != nil {
			return notFoundOrForbidden(e, err)
		}
		if chapters, _, err := s.Store.LoadJobChapters(job); err != nil {
			slog.Error("load job chapters for processing mark", "jobId", job.ID, "error", err)
		} else {
			chapterIDs := make([]string, 0, len(chapters))
			for _, chapter := range chapters {
				chapterIDs = append(chapterIDs, chapter.ID)
			}
			if err := s.Store.UpdateChaptersStatusFast(chapterIDs, "processing", ""); err != nil {
				slog.Error("mark job chapters processing", "jobId", job.ID, "error", err)
			}
		}
		s.enqueueJob(job.ID)
		return e.JSON(http.StatusCreated, jobRecord(*job))
	})
	api.GET("/db/novels/{novelId}/translation-jobs", func(e *core.RequestEvent) error {
		failedOnly := e.Request.URL.Query().Get("failedOnly") == "1"
		jobs, err := s.Store.ListJobs(e.Auth.Id, e.Request.PathValue("novelId"), failedOnly)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		out := make([]map[string]any, 0, len(jobs))
		for _, job := range jobs {
			out = append(out, jobRecord(job))
		}
		return e.JSON(http.StatusOK, out)
	})
	api.GET("/db/translation-jobs/active/status", func(e *core.RequestEvent) error {
		hasActive, err := s.Store.HasActiveJobs(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to read active job status", err)
		}
		return e.JSON(http.StatusOK, map[string]any{"hasActive": hasActive})
	})
	api.GET("/db/translation-jobs/active", func(e *core.RequestEvent) error {
		jobs, err := s.Store.ListActiveJobs(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to list active jobs", err)
		}
		out := make([]map[string]any, 0, len(jobs))
		for _, job := range jobs {
			out = append(out, jobRecord(job))
		}
		return e.JSON(http.StatusOK, out)
	})
	api.PATCH("/db/translation-jobs/{jobId}", func(e *core.RequestEvent) error {
		patch := map[string]any{}
		if err := e.BindBody(&patch); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		jobId := e.Request.PathValue("jobId")
		if err := s.Store.UpdateJobForUser(e.Auth.Id, jobId, patch); err != nil {
			return notFoundOrForbidden(e, err)
		}
		if status, _ := patch["status"].(string); status == "pending" {
			s.enqueueJob(jobId)
		} else if status == "cancelled" {
			s.cancelJob(jobId)
			if err := s.Store.ReconcileProcessingChaptersForJob(jobId); err != nil {
				slog.Error("reconcile cancelled job chapters", "jobId", jobId, "error", err)
			}
		}
		job, err := s.Store.GetOwnedJob(e.Auth.Id, e.Request.PathValue("jobId"))
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		return e.JSON(http.StatusOK, jobRecord(*job))
	})
}
