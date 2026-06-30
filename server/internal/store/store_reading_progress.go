package store

import (
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
)

func (s *Store) GetReadingProgress(userID, novelID string) (*ReadingProgress, error) {
	record, err := s.App.FindFirstRecordByFilter(
		ReadingProgressCollection,
		"user = {:user} && novel = {:novel}",
		dbx.Params{"user": userID, "novel": novelID},
	)
	if err != nil {
		return nil, err
	}
	rp := readingProgressFromRecord(record)
	return &rp, nil
}

func (s *Store) UpsertReadingProgress(userID, novelID, chapterID string, scrollPercent float64) (*ReadingProgress, error) {
	collection, err := s.App.FindCollectionByNameOrId(ReadingProgressCollection)
	if err != nil {
		return nil, err
	}

	record, err := s.App.FindFirstRecordByFilter(
		ReadingProgressCollection,
		"user = {:user} && novel = {:novel}",
		dbx.Params{"user": userID, "novel": novelID},
	)
	if err != nil {
		record = core.NewRecord(collection)
		record.Set("user", userID)
		record.Set("novel", novelID)
	}

	record.Set("chapter_id", chapterID)
	record.Set("scroll_percent", scrollPercent)

	if err := s.App.Save(record); err != nil {
		return nil, err
	}

	rp := readingProgressFromRecord(record)
	return &rp, nil
}
