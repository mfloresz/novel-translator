package store

import (
	"encoding/json"
	"sort"
	"strings"

	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

func (s *Store) CreateJob(userID string, job *Job) error {
	if _, err := s.GetOwnedNovel(userID, job.NovelID); err != nil {
		return err
	}
	collection, err := s.App.FindCollectionByNameOrId(JobsCollection)
	if err != nil {
		return err
	}
	record := core.NewRecord(collection)
	record.Set("owner", userID)
	record.Set("novel", job.NovelID)
	record.Set("status", defaultString(job.Status, "pending"))
	record.Set("operation", defaultString(job.Operation, "translate"))
	record.Set("provider", job.Provider)
	record.Set("model", job.Model)
	record.Set("chapter_ids", defaultString(job.ChapterIDs, "[]"))
	record.Set("options_json", defaultString(job.OptionsJSON, "{}"))
	record.Set("error_message", job.ErrorMessage)
	record.Set("total_chapters", job.TotalChapters)
	record.Set("completed_chapters", job.CompletedChapters)
	record.Set("failed_chapters", job.FailedChapters)
	record.Set("auto_segment_enabled", job.AutoSegmentEnabled)
	record.Set("auto_segment_active", job.AutoSegmentActive)
	record.Set("auto_segment_count", job.AutoSegmentCount)
	record.Set("auto_segment_current_index", job.AutoSegmentCurrentIndex)
	record.Set("auto_segment_completed_count", job.AutoSegmentCompletedCount)
	record.Set("auto_segment_chapter_id", job.AutoSegmentChapterID)
	record.Set("auto_segment_chapter_title", job.AutoSegmentChapterTitle)
	if err := s.App.Save(record); err != nil {
		return err
	}
	stored := jobFromRecord(record)
	*job = stored
	return nil
}

func (s *Store) GetJob(jobID string) (*Job, error) {
	record, err := s.App.FindRecordById(JobsCollection, jobID)
	if err != nil {
		return nil, ErrNotFound
	}
	job := jobFromRecord(record)
	return &job, nil
}

func (s *Store) GetOwnedJob(userID, jobID string) (*Job, error) {
	record, err := s.App.FindRecordById(JobsCollection, jobID)
	if err != nil {
		return nil, ErrNotFound
	}
	if record.GetString("owner") != userID {
		return nil, ErrForbidden
	}
	job := jobFromRecord(record)
	return &job, nil
}

func (s *Store) ListRunnableJobs() ([]Job, error) {
	records, err := s.App.FindRecordsByFilter(JobsCollection, "status = 'pending' || status = 'running'", "created", 500, 0)
	if err != nil {
		return nil, err
	}
	out := make([]Job, 0, len(records))
	for _, record := range records {
		out = append(out, jobFromRecord(record))
	}
	return out, nil
}

func (s *Store) ListJobs(userID, novelID string, failedOnly bool) ([]Job, error) {
	if _, err := s.GetNovelAccessible(userID, novelID); err != nil {
		return nil, err
	}
	filter := "owner = {:owner} && novel = {:novel}"
	if failedOnly {
		filter += " && (status = 'failed' || failed_chapters > 0)"
	}
	records, err := s.App.FindRecordsByFilter(JobsCollection, filter, "-created", 200, 0, dbx.Params{"owner": userID, "novel": novelID})
	if err != nil {
		return nil, err
	}
	out := make([]Job, 0, len(records))
	for _, record := range records {
		out = append(out, jobFromRecord(record))
	}
	return out, nil
}

func (s *Store) ListActiveJobs(userID string) ([]Job, error) {
	records, err := s.App.FindRecordsByFilter(JobsCollection, "owner = {:owner} && (status = 'pending' || status = 'running')", "-created", 200, 0, dbx.Params{"owner": userID})
	if err != nil {
		return nil, err
	}
	out := make([]Job, 0, len(records))
	for _, record := range records {
		job := jobFromRecord(record)
		novel, _ := s.App.FindRecordById(NovelsCollection, job.NovelID)
		if novel != nil {
			job.NovelTitle = defaultString(novel.GetString("target_title"), novel.GetString("source_title"))
		}
		out = append(out, job)
	}
	return out, nil
}

func (s *Store) HasActiveJobs(userID string) (bool, error) {
	records, err := s.App.FindRecordsByFilter(JobsCollection, "owner = {:owner} && (status = 'pending' || status = 'running')", "", 1, 0, dbx.Params{"owner": userID})
	if err != nil {
		return false, err
	}
	return len(records) > 0, nil
}

func (s *Store) UpdateJob(jobID string, patch map[string]any) error {
	record, err := s.App.FindRecordById(JobsCollection, jobID)
	if err != nil {
		return ErrNotFound
	}
	if record.GetString("status") == "cancelled" {
		if nextStatus, ok := patch["status"].(string); !ok || nextStatus != "cancelled" {
			return nil
		}
	}
	for key, value := range patch {
		switch key {
		case "status", "operation", "provider", "model", "errorMessage",
			"autoSegmentEnabled", "autoSegmentActive", "autoSegmentChapterId", "autoSegmentChapterTitle":
			record.Set(camelToSnake(key), value)
		case "completedChapters", "failedChapters", "totalChapters", "autoSegmentCount", "autoSegmentCurrentIndex", "autoSegmentCompletedCount":
			record.Set(camelToSnake(key), value)
		}
	}
	return s.App.Save(record)
}

func (s *Store) UpdateJobForUser(userID, jobID string, patch map[string]any) error {
	record, err := s.App.FindRecordById(JobsCollection, jobID)
	if err != nil {
		return ErrNotFound
	}
	if record.GetString("owner") != userID {
		return ErrForbidden
	}
	for key, value := range patch {
		switch key {
		case "status", "operation", "provider", "model", "errorMessage",
			"autoSegmentEnabled", "autoSegmentActive", "autoSegmentChapterId", "autoSegmentChapterTitle":
			record.Set(camelToSnake(key), value)
		case "completedChapters", "failedChapters", "totalChapters", "autoSegmentCount", "autoSegmentCurrentIndex", "autoSegmentCompletedCount":
			record.Set(camelToSnake(key), value)
		}
	}
	return s.App.Save(record)
}

func (s *Store) LoadJobChapters(job *Job) ([]Chapter, *Novel, error) {
	novel, err := s.GetOwnedNovel(job.OwnerID, job.NovelID)
	if err != nil {
		return nil, nil, err
	}
	chapters, err := s.ListChaptersAccessible(job.OwnerID, job.NovelID)
	if err != nil {
		return nil, nil, err
	}
	selected := chapters
	if strings.TrimSpace(job.ChapterIDs) != "" && job.ChapterIDs != "[]" {
		var ids []string
		_ = json.Unmarshal([]byte(job.ChapterIDs), &ids)
		allowed := map[string]bool{}
		for _, id := range ids {
			allowed[id] = true
		}
		selected = make([]Chapter, 0, len(ids))
		for _, chapter := range chapters {
			if allowed[chapter.ID] {
				selected = append(selected, chapter)
			}
		}
	}
	sort.Slice(selected, func(i, j int) bool { return selected[i].ChapterOrder < selected[j].ChapterOrder })
	return selected, novel, nil
}

func (s *Store) removeDeletedChapterReferences(novelID string, deletedIDs []string) error {
	if len(deletedIDs) == 0 {
		return nil
	}
	deleted := make(map[string]struct{}, len(deletedIDs))
	for _, id := range deletedIDs {
		if trimmed := strings.TrimSpace(id); trimmed != "" {
			deleted[trimmed] = struct{}{}
		}
	}
	if len(deleted) == 0 {
		return nil
	}
	records, err := s.App.FindRecordsByFilter(JobsCollection, "novel = {:novel}", "", 500, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return err
	}
	for _, record := range records {
		changed := false
		if raw := strings.TrimSpace(record.GetString("chapter_ids")); raw != "" && raw != "[]" {
			var ids []string
			if err := json.Unmarshal([]byte(raw), &ids); err == nil {
				pruned := make([]string, 0, len(ids))
				for _, id := range ids {
					if _, shouldDelete := deleted[id]; shouldDelete {
						changed = true
						continue
					}
					pruned = append(pruned, id)
				}
				if changed {
					encoded, err := json.Marshal(pruned)
					if err != nil {
						return err
					}
					record.Set("chapter_ids", string(encoded))
					status := record.GetString("status")
					if status == "pending" || status == "running" {
						record.Set("total_chapters", len(pruned))
					}
				}
			}
		}
		if current := strings.TrimSpace(record.GetString("auto_segment_chapter_id")); current != "" {
			if _, shouldClear := deleted[current]; shouldClear {
				record.Set("auto_segment_chapter_id", "")
				record.Set("auto_segment_chapter_title", "")
				changed = true
			}
		}
		if changed {
			if err := s.App.Save(record); err != nil {
				return err
			}
		}
	}
	return nil
}
