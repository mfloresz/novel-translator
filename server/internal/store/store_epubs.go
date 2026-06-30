package store

import (
	"github.com/pocketbase/dbx"
	"github.com/pocketbase/pocketbase/core"
	"github.com/pocketbase/pocketbase/tools/filesystem"
)

func (s *Store) UpsertEpub(userID string, epub *Epub, fileName, mimeType string, fileBlob []byte) (*Epub, error) {
	if _, err := s.GetOwnedNovel(userID, epub.NovelID); err != nil {
		return nil, err
	}
	record, err := s.App.FindFirstRecordByFilter(EpubsCollection, "novel = {:novel} && file_kind = {:kind} && source_variant = {:variant}", dbx.Params{"novel": epub.NovelID, "kind": epub.FileKind, "variant": epub.SourceVariant})
	if err != nil {
		collection, cErr := s.App.FindCollectionByNameOrId(EpubsCollection)
		if cErr != nil {
			return nil, cErr
		}
		record = core.NewRecord(collection)
		record.Set("novel", epub.NovelID)
		record.Set("file_kind", epub.FileKind)
		record.Set("source_variant", epub.SourceVariant)
	}
	record.Set("label", epub.Label)
	if len(fileBlob) > 0 {
		file, err := filesystem.NewFileFromBytes(fileBlob, fileName)
		if err != nil {
			return nil, err
		}
		record.Set("file", []*filesystem.File{file})
	}
	if err := s.App.Save(record); err != nil {
		return nil, err
	}
	stored := epubFromRecord(record)
	return &stored, nil
}

func (s *Store) ListEpubs(userID, novelID string) ([]Epub, error) {
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return nil, err
	}
	records, err := s.App.FindRecordsByFilter(EpubsCollection, "novel = {:novel}", "-created", 100, 0, dbx.Params{"novel": novelID})
	if err != nil {
		return nil, err
	}
	out := make([]Epub, 0, len(records))
	for _, record := range records {
		out = append(out, epubFromRecord(record))
	}
	return out, nil
}

func (s *Store) GetEpubDownloadFile(userID, epubID string) (*core.Record, string, error) {
	record, err := s.App.FindRecordById(EpubsCollection, epubID)
	if err != nil {
		return nil, "", ErrNotFound
	}
	novelID := record.GetString("novel")
	if _, err := s.GetOwnedNovel(userID, novelID); err != nil {
		return nil, "", err
	}
	files := record.GetStringSlice("file")
	if len(files) == 0 {
		return nil, "", ErrNotFound
	}
	return record, files[0], nil
}
