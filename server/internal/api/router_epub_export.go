package api

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/epubexport"
	"translator-server/internal/store"
)

func registerEpubExportRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.POST("/epubs/build", func(e *core.RequestEvent) error {
		body := struct {
			NovelID string `json:"novelId"`
			Source  string `json:"source"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}

		body.Source = strings.ToLower(strings.TrimSpace(body.Source))
		switch body.Source {
		case "original", "translated", "refined":
		default:
			return e.BadRequestError("source must be original, translated, or refined", nil)
		}

		novel, err := s.Store.GetOwnedNovel(e.Auth.Id, body.NovelID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}

		chapters, err := s.Store.ListChaptersAccessible(e.Auth.Id, body.NovelID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}

		meta := buildEpubMeta(novel, body.Source)

		var coverBytes []byte
		var coverMime string
		if novel.CoverFile != "" {
			if novelRecord, nErr := e.App.FindRecordById(store.NovelsCollection, novel.ID); nErr == nil {
				fsys, fErr := e.App.NewFilesystem()
				if fErr == nil {
					defer fsys.Close()
					fileKey := novelRecord.BaseFilesPath() + "/" + novel.CoverFile
					if reader, rErr := fsys.GetReader(fileKey); rErr == nil {
						defer reader.Close()
						coverBytes, _ = epubexport.ReadCloserToBytes(reader)
						coverMime = epubexport.DetectImageMime(coverBytes)
					}
				}
			}
		}

		epubChapters := buildEpubChapters(chapters, body.Source)
		if len(epubChapters) == 0 {
			return e.BadRequestError("no chapters with content for the selected source", nil)
		}

		epubBytes, err := epubexport.GenerateEpubFile(meta, epubChapters, coverBytes, coverMime)
		if err != nil {
			return e.InternalServerError("failed to generate epub", err)
		}

		fileName := sanitizeFileName(meta.Title) + ".epub"
		fileKind := "translated"
		if body.Source == "original" {
			fileKind = "original"
		}
		sourceVariant := body.Source

		item, err := s.Store.UpsertEpub(e.Auth.Id, &store.Epub{
			NovelID:       body.NovelID,
			FileKind:      fileKind,
			SourceVariant: sourceVariant,
			Label:         fmt.Sprintf("source=%s", body.Source),
		}, fileName, "application/epub+zip", epubBytes)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}

		return e.JSON(http.StatusCreated, epubRecord(*item))
	})
}

func buildEpubMeta(novel *store.Novel, source string) epubexport.EpubMetadata {
	title := novel.SourceTitle
	author := novel.SourceAuthor
	description := novel.SourceDescription
	language := novel.SourceLanguage
	series := novel.SourceSeries
	number := novel.SourceNumber

	if source == "translated" || source == "refined" {
		if novel.TargetTitle != "" {
			title = novel.TargetTitle
		}
		if novel.TargetAuthor != "" {
			author = novel.TargetAuthor
		}
		if novel.TargetDescription != "" {
			description = novel.TargetDescription
		}
		if novel.TargetLanguage != "" {
			language = novel.TargetLanguage
		}
		if novel.TargetSeries != "" {
			series = novel.TargetSeries
		}
		if novel.TargetNumber != "" {
			number = novel.TargetNumber
		}
	}

	if title == "" {
		title = "Untitled"
	}
	if author == "" {
		author = "Unknown"
	}
	if language == "" {
		language = "es"
	}

	return epubexport.EpubMetadata{
		Title:       title,
		Author:      author,
		Description: description,
		Language:    language,
		Publisher:   "NovelTranslator",
		Series:      series,
		Number:      number,
	}
}

func buildEpubChapters(chapters []store.Chapter, source string) []epubexport.ChapterData {
	var result []epubexport.ChapterData
	for _, ch := range chapters {
		var content string
		var title string

		switch source {
		case "original":
			content = ch.OriginalContent
			title = ch.Title
		case "translated":
			content = ch.TranslatedContent
			title = ch.TranslatedTitle
			if title == "" {
				title = ch.Title
			}
		case "refined":
			content = ch.RefinedContent
			if content == "" {
				content = ch.TranslatedContent
			}
			if content == "" {
				content = ch.OriginalContent
			}
			title = ch.TranslatedTitle
			if title == "" {
				title = ch.Title
			}
		}

		content = strings.TrimSpace(content)
		if content == "" {
			continue
		}

		if title == "" {
			title = fmt.Sprintf("Chapter %d", ch.ChapterOrder)
		}

		result = append(result, epubexport.ChapterData{
			Title:   title,
			Content: content,
		})
	}
	return result
}

func sanitizeFileName(title string) string {
	if title == "" {
		return "libro"
	}
	r := strings.NewReplacer(
		"\\", "_", "/", "_", ":", "_", "*", "_",
		"?", "_", "\"", "_", "<", "_", ">", "_", "|", "_",
	)
	clean := r.Replace(title)
	if len(clean) > 120 {
		clean = clean[:120]
	}
	return clean
}
