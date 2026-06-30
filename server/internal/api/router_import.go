package api

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"mime"
	"net/http"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/pocketbase/pocketbase/core"
	pbrouter "github.com/pocketbase/pocketbase/tools/router"
	"translator-server/internal/epubimport"
	"translator-server/internal/noveldownloader"
	"translator-server/internal/store"
)

var chapterOrderRegex = regexp.MustCompile(`(\d+)`)

const previewCacheTTL = 15 * time.Minute

type previewCacheEntry struct {
	chapters  []noveldownloader.ChapterURL
	createdAt time.Time
}

func registerImportRoutes(api *pbrouter.RouterGroup[*core.RequestEvent], s *Server) {
	api.POST("/db/novels/import-epub", func(e *core.RequestEvent) error {
		if err := e.Request.ParseMultipartForm(64 << 20); err != nil {
			return e.BadRequestError("invalid multipart", err)
		}
		file, header, err := e.Request.FormFile("file")
		if err != nil {
			return e.BadRequestError("file required", err)
		}
		defer file.Close()
		blob, err := io.ReadAll(file)
		if err != nil {
			return e.InternalServerError("failed to read file", err)
		}
		parsed, err := epubimport.Parse(blob, header.Filename)
		if err != nil {
			return e.BadRequestError("parse error", err)
		}
		sourceLang := strings.TrimSpace(e.Request.FormValue("sourceLanguage"))
		if sourceLang == "" {
			sourceLang = parsed.Language
		}
		targetLang := strings.TrimSpace(e.Request.FormValue("targetLanguage"))
		if sourceLang == "" || targetLang == "" {
			return e.BadRequestError("sourceLanguage and targetLanguage are required", nil)
		}
		chapters := make([]store.ImportedEpubChapter, len(parsed.Chapters))
		for i, ch := range parsed.Chapters {
			chapters[i] = store.ImportedEpubChapter{Title: ch.Title, Content: ch.Content}
		}
		mimeType := header.Header.Get("Content-Type")
		if mimeType == "" {
			mimeType = mime.TypeByExtension(".epub")
			if mimeType == "" {
				mimeType = "application/epub+zip"
			}
		}
		result, err := s.Store.ImportEpubNovel(&store.ImportEpubNovelInput{OwnerID: e.Auth.Id, FileName: header.Filename, FileBlob: blob, MimeType: mimeType, SourceTitle: parsed.Title, SourceAuthor: parsed.Author, SourceDescription: parsed.Description, SourceLanguage: sourceLang, TargetLanguage: targetLang, SourceSeries: parsed.Series, SourceNumber: parsed.Number, CoverBlob: parsed.CoverBlob, CoverMime: parsed.CoverMime, Chapters: chapters})
		if err != nil {
			return e.InternalServerError("failed to import epub", err)
		}
		return e.JSON(http.StatusCreated, map[string]any{"novel": parseJSONFields(&result.Novel), "epub": epubRecord(result.Epub), "chaptersImported": result.ChaptersImported})
	})
	api.POST("/db/novels/import-from-zip", func(e *core.RequestEvent) error {
		if err := e.Request.ParseMultipartForm(256 << 20); err != nil {
			return e.BadRequestError("invalid multipart", err)
		}
		file, header, err := e.Request.FormFile("file")
		if err != nil {
			return e.BadRequestError("file required", err)
		}
		defer file.Close()
		blob, err := io.ReadAll(file)
		if err != nil {
			return e.InternalServerError("failed to read file", err)
		}
		reader, err := zip.NewReader(strings.NewReader(string(blob)), int64(len(blob)))
		if err != nil {
			return e.BadRequestError("invalid zip file", err)
		}
		rawEntries := make([]struct {
			name    string
			content []byte
		}, 0)
		for _, f := range reader.File {
			if f.FileInfo().IsDir() {
				continue
			}
			rc, openErr := f.Open()
			if openErr != nil {
				return e.InternalServerError("failed to read zip entry", openErr)
			}
			data, readErr := io.ReadAll(rc)
			rc.Close()
			if readErr != nil {
				return e.InternalServerError("failed to read zip entry", readErr)
			}
			name := strings.TrimLeft(filepath.ToSlash(f.Name), "./")
			rawEntries = append(rawEntries, struct {
				name    string
				content []byte
			}{name, data})
		}
		prefix := detectZipRoot(rawEntries)
		var metadataJSON string
		var coverBlob []byte
		var coverMime string
		type zipFile struct {
			name    string
			content string
		}
		originals := map[string]zipFile{}
		translated := map[string]zipFile{}
		for _, e := range rawEntries {
			normalized := strings.TrimPrefix(e.name, prefix)
			slog.Debug("zip entry", "raw", e.name, "normalized", normalized)
			lower := strings.ToLower(normalized)
			switch {
			case lower == "metadata.json":
				metadataJSON = string(e.content)
			case strings.HasPrefix(lower, "cover."):
				coverBlob = e.content
				ext := strings.ToLower(filepath.Ext(normalized))
				switch ext {
				case ".jpg", ".jpeg":
					coverMime = "image/jpeg"
				case ".png":
					coverMime = "image/png"
				case ".gif":
					coverMime = "image/gif"
				case ".webp":
					coverMime = "image/webp"
				default:
					coverMime = "image/jpeg"
				}
			case strings.HasPrefix(lower, "originals/"):
				name := normalized[len("originals/"):]
				if name != "" {
					originals[name] = zipFile{name: name, content: string(e.content)}
				}
			case strings.HasPrefix(lower, "translated/"):
				name := normalized[len("translated/"):]
				if name != "" {
					translated[name] = zipFile{name: name, content: string(e.content)}
				}
			}
		}
		if metadataJSON == "" {
			return e.BadRequestError("metadata.json is required in the zip", nil)
		}
		if len(originals) == 0 {
			return e.BadRequestError("originals/ directory is required in the zip", nil)
		}
		type namedFile struct {
			name    string
			content string
			number  int
		}
		sorted := make([]namedFile, 0, len(originals))
		for name, f := range originals {
			sorted = append(sorted, namedFile{name: name, content: f.content, number: extractChapterOrder(name)})
		}
		sort.Slice(sorted, func(i, j int) bool {
			return sorted[i].number < sorted[j].number
		})
		chapters := make([]store.ImportedZipChapter, 0, len(sorted))
		for idx, entry := range sorted {
			title := extractChapterTitle(entry.content, entry.name)
			origContent := contentAfterTitle(entry.content)
			transContent := ""
			transTitle := ""
			if t, ok := translated[entry.name]; ok {
				transContent = contentAfterTitle(t.content)
				transTitle = extractChapterTitle(t.content, entry.name)
			}
			chapters = append(chapters, store.ImportedZipChapter{
				Order:             idx + 1,
				Title:             title,
				TranslatedTitle:   transTitle,
				OriginalContent:   origContent,
				TranslatedContent: transContent,
			})
		}
		result, err := s.Store.ImportZipNovel(&store.ImportZipNovelInput{
			OwnerID:      e.Auth.Id,
			FileName:     header.Filename,
			FileBlob:     blob,
			MetadataJSON: metadataJSON,
			CoverBlob:    coverBlob,
			CoverMime:    coverMime,
			Chapters:     chapters,
		})
		if err != nil {
			return e.InternalServerError("failed to import zip novel", err)
		}
		return e.JSON(http.StatusCreated, map[string]any{"novel": parseJSONFields(&result.Novel), "chaptersImported": result.ChaptersImported})
	})
	api.POST("/db/novels/preview-from-url", func(e *core.RequestEvent) error {
		body := struct {
			URL string `json:"url"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if strings.TrimSpace(body.URL) == "" {
			return e.BadRequestError("url is required", nil)
		}
		dl := s.DownloaderFactory()
		parser := dl.FindParser(body.URL)
		if parser == nil {
			return e.BadRequestError("unsupported URL: only novelfire.net, novelbin.com, and fenrirealm.com are supported", nil)
		}
		info, err := dl.GetNovelInfo(e.Request.Context(), body.URL)
		if err != nil {
			return e.InternalServerError("failed to fetch novel info", err)
		}
		return e.JSON(http.StatusOK, map[string]any{
			"title":         info.Title,
			"author":        info.Author,
			"description":   info.Description,
			"coverURL":      info.CoverURL,
			"totalChapters": len(info.Chapters),
			"sourceURL":     info.SourceURL,
		})
	})
	api.POST("/db/novels/import-from-url", func(e *core.RequestEvent) error {
		body := struct {
			URL            string `json:"url"`
			SourceLanguage string `json:"sourceLanguage"`
			TargetLanguage string `json:"targetLanguage"`
			StartChapter   int    `json:"startChapter"`
			EndChapter     int    `json:"endChapter"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if strings.TrimSpace(body.URL) == "" {
			return e.BadRequestError("url is required", nil)
		}
		sourceLang := strings.TrimSpace(body.SourceLanguage)
		if sourceLang == "" {
			sourceLang = "en"
		}
		targetLang := strings.TrimSpace(body.TargetLanguage)
		if targetLang == "" {
			targetLang = "es"
		}
		dl := s.DownloaderFactory()
		parser := dl.FindParser(body.URL)
		if parser == nil {
			return e.BadRequestError("unsupported URL: only novelfire.net, novelbin.com, and fenrirealm.com are supported", nil)
		}
		info, err := dl.GetNovelInfo(e.Request.Context(), body.URL)
		if err != nil {
			return e.InternalServerError("failed to fetch novel info", err)
		}
		startCh := body.StartChapter
		if startCh < 1 {
			startCh = 1
		}
		endCh := body.EndChapter
		if endCh < startCh || endCh > len(info.Chapters) {
			endCh = len(info.Chapters)
		}
		firstChapter, err := dl.DownloadChapters(e.Request.Context(), info.Chapters, startCh, startCh)
		if err != nil {
			return e.InternalServerError("failed to download first chapter", err)
		}
		if len(firstChapter) == 0 {
			return e.InternalServerError("failed to download first chapter", fmt.Errorf("no content returned"))
		}
		result, err := s.Store.ImportUrlNovel(&store.ImportUrlNovelInput{
			OwnerID:           e.Auth.Id,
			URL:               body.URL,
			SourceLanguage:    sourceLang,
			TargetLanguage:    targetLang,
			SourceTitle:       info.Title,
			SourceAuthor:      info.Author,
			SourceDescription: info.Description,
			StartChapter:      startCh,
			EndChapter:        endCh,
		})
		if err != nil {
			return e.InternalServerError("failed to create novel", err)
		}
		ch := firstChapter[0]
		chTitle := ch.Title
		if chTitle == "" {
			chTitle = fmt.Sprintf("Capítulo %d", startCh)
		}
		if _, err := s.Store.UpsertChapterWithoutStats(e.Auth.Id, result.Novel.ID, &store.Chapter{
			ChapterOrder:    startCh,
			Title:           chTitle,
			OriginalContent: ch.Markdown,
			Status:          "pending",
		}); err != nil {
			return e.InternalServerError("failed to save chapter", err)
		}

		if info.CoverURL != "" {
			coverBlob, coverMime, coverErr := dl.DownloadCover(e.Request.Context(), info.CoverURL)
			if coverErr != nil {
				slog.Warn("failed to download cover", "novel", result.Novel.ID, "error", coverErr)
			} else if err := s.Store.AttachCoverBlob(result.Novel.ID, coverBlob, coverMime); err != nil {
				slog.Warn("failed to attach cover", "novel", result.Novel.ID, "error", err)
			}
		}
		if err := s.Store.RecalculateNovelStats(result.Novel.ID); err != nil {
			slog.Warn("failed to recalculate novel stats", "novel", result.Novel.ID, "error", err)
		}
		remainingChapters := make([]store.DownloadChapterInfo, 0)
		for i := startCh; i < endCh; i++ {
			chURL := info.Chapters[i]
			chTitle := chURL.Title
			if chTitle == "" {
				chTitle = fmt.Sprintf("Capítulo %d", i+1)
			}
			remainingChapters = append(remainingChapters, store.DownloadChapterInfo{
				URL:   chURL.URL,
				Title: chTitle,
			})
		}
		var downloadJobID string
		if len(remainingChapters) > 0 {
			optionsJSON, _ := json.Marshal(map[string]any{
				"url":            body.URL,
				"chapters":       remainingChapters,
				"startOrder":     startCh + 1,
				"sourceLanguage": sourceLang,
				"targetLanguage": targetLang,
			})
			job := &store.Job{
				NovelID:       result.Novel.ID,
				Status:        "pending",
				Operation:     "download",
				ChapterIDs:    "[]",
				OptionsJSON:   string(optionsJSON),
				TotalChapters: len(remainingChapters),
			}
			if err := s.Store.CreateJob(e.Auth.Id, job); err != nil {
				slog.Error("failed to create download job", "novel", result.Novel.ID, "error", err)
			} else {
				s.enqueueJob(job.ID)
				downloadJobID = job.ID
			}
		}
		novel, err := s.Store.GetOwnedNovel(e.Auth.Id, result.Novel.ID)
		if err != nil {
			return e.InternalServerError("failed to reload novel", err)
		}
		resp := map[string]any{
			"novel":            parseJSONFields(novel),
			"chaptersImported": 1,
			"totalChapters":    len(info.Chapters),
		}
		if downloadJobID != "" {
			resp["downloadJob"] = map[string]any{
				"id":            downloadJobID,
				"totalChapters": len(remainingChapters),
			}
		}
		return e.JSON(http.StatusCreated, resp)
	})
	api.GET("/db/novels/{id}/update-preview", func(e *core.RequestEvent) error {
		novelID := e.Request.PathValue("id")
		novel, err := s.Store.GetOwnedNovel(e.Auth.Id, novelID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		if strings.TrimSpace(novel.URL) == "" {
			return e.BadRequestError("novel has no source URL", nil)
		}
		dl := s.DownloaderFactory()
		info, err := dl.GetNovelInfo(e.Request.Context(), novel.URL)
		if err != nil {
			return e.InternalServerError("failed to fetch novel info", err)
		}
		cacheKey := e.Auth.Id + ":" + novelID
		s.previewCacheMu.Lock()
		s.previewCache[cacheKey] = previewCacheEntry{
			chapters:  info.Chapters,
			createdAt: time.Now(),
		}
		s.previewCacheMu.Unlock()
		time.AfterFunc(previewCacheTTL, func() {
			s.previewCacheMu.Lock()
			defer s.previewCacheMu.Unlock()
			if entry, exists := s.previewCache[cacheKey]; exists {
				if time.Since(entry.createdAt) >= previewCacheTTL {
					delete(s.previewCache, cacheKey)
				}
			}
		})
		maxOrder, err := s.Store.GetMaxChapterOrder(e.Auth.Id, novelID)
		if err != nil {
			return e.InternalServerError("failed to get max chapter order", err)
		}
		existingTitles, err := s.Store.GetExistingChapterURLs(e.Auth.Id, novelID)
		if err != nil {
			return e.InternalServerError("failed to check existing chapters", err)
		}
		newAvailable := 0
		firstNew := 0
		lastNew := 0
		for _, ch := range info.Chapters {
			chNum := extractChapterOrder(ch.Title)
			if chNum > 0 && chNum <= maxOrder {
				continue
			}
			if existingTitles[ch.Title] {
				continue
			}
			newAvailable++
			if chNum > 0 {
				if firstNew == 0 || chNum < firstNew {
					firstNew = chNum
				}
				if chNum > lastNew {
					lastNew = chNum
				}
			}
		}
		return e.JSON(http.StatusOK, map[string]any{
			"title":           info.Title,
			"author":          info.Author,
			"description":     info.Description,
			"coverURL":        info.CoverURL,
			"sourceURL":       info.SourceURL,
			"currentChapters": len(existingTitles),
			"totalChapters":   len(info.Chapters),
			"newChapters":     newAvailable,
			"firstNewChapter": firstNew,
			"lastNewChapter":  lastNew,
		})
	})
	api.POST("/db/novels/{id}/update-from-url", func(e *core.RequestEvent) error {
		body := struct {
			StartChapter int `json:"startChapter"`
			EndChapter   int `json:"endChapter"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		novelID := e.Request.PathValue("id")
		novel, err := s.Store.GetOwnedNovel(e.Auth.Id, novelID)
		if err != nil {
			return notFoundOrForbidden(e, err)
		}
		if strings.TrimSpace(novel.URL) == "" {
			return e.BadRequestError("novel has no source URL", nil)
		}
		cacheKey := e.Auth.Id + ":" + novelID
		s.previewCacheMu.RLock()
		cached, found := s.previewCache[cacheKey]
		s.previewCacheMu.RUnlock()

		var chapters []noveldownloader.ChapterURL
		if found {
			chapters = cached.chapters
			s.previewCacheMu.Lock()
			delete(s.previewCache, cacheKey)
			s.previewCacheMu.Unlock()
		} else {
			dl := s.DownloaderFactory()
			info, err := dl.GetNovelInfo(e.Request.Context(), novel.URL)
			if err != nil {
				return e.InternalServerError("failed to fetch novel info", err)
			}
			chapters = info.Chapters
		}
		maxOrder, err := s.Store.GetMaxChapterOrder(e.Auth.Id, novelID)
		if err != nil {
			return e.InternalServerError("failed to get max chapter order", err)
		}
		existingTitles, err := s.Store.GetExistingChapterURLs(e.Auth.Id, novelID)
		if err != nil {
			return e.InternalServerError("failed to check existing chapters", err)
		}
		sourceToDownload := make([]int, 0)
		for i, ch := range chapters {
			chNum := extractChapterOrder(ch.Title)
			if chNum > 0 && chNum <= maxOrder {
				continue
			}
			if existingTitles[ch.Title] {
				continue
			}
			pos := chNum
			if pos <= 0 {
				pos = i + 1
			}
			if body.StartChapter > 0 && pos < body.StartChapter {
				continue
			}
			if body.EndChapter > 0 && pos > body.EndChapter {
				continue
			}
			sourceToDownload = append(sourceToDownload, i)
		}
		if len(sourceToDownload) == 0 {
			return e.JSON(http.StatusOK, map[string]any{"chaptersAdded": 0, "chapters": []map[string]any{}, "totalChapters": len(chapters), "message": "No hay capítulos nuevos. La novela ya está al día."})
		}
		downloadChapters := make([]store.DownloadChapterInfo, 0, len(sourceToDownload))
		for _, srcIdx := range sourceToDownload {
			ch := chapters[srcIdx]
			chTitle := ch.Title
			if chTitle == "" {
				chTitle = fmt.Sprintf("Capítulo %d", srcIdx+1)
			}
			downloadChapters = append(downloadChapters, store.DownloadChapterInfo{
				URL:   ch.URL,
				Title: chTitle,
			})
		}
		firstNewOrder := extractChapterOrder(chapters[sourceToDownload[0]].Title)
		if firstNewOrder <= 0 {
			firstNewOrder = sourceToDownload[0] + 1
		}
		optionsJSON, _ := json.Marshal(map[string]any{
			"url":            novel.URL,
			"chapters":       downloadChapters,
			"startOrder":     firstNewOrder,
			"sourceLanguage": novel.SourceLanguage,
			"targetLanguage": novel.TargetLanguage,
		})
		job := &store.Job{
			NovelID:       novelID,
			Status:        "pending",
			Operation:     "download",
			ChapterIDs:    "[]",
			OptionsJSON:   string(optionsJSON),
			TotalChapters: len(downloadChapters),
		}
		if err := s.Store.CreateJob(e.Auth.Id, job); err != nil {
			return e.InternalServerError("failed to create download job", err)
		}
		s.enqueueJob(job.ID)
		return e.JSON(http.StatusOK, map[string]any{
			"chaptersAdded":   0,
			"chapters":        []map[string]any{},
			"totalChapters":   len(chapters),
			"pendingChapters": len(downloadChapters),
			"downloadJobId":   job.ID,
			"message":         fmt.Sprintf("Descarga iniciada. %d capítulos se están descargando en segundo plano.", len(downloadChapters)),
		})
	})
	api.GET("/db/novels/check-batch-updates", func(e *core.RequestEvent) error {
		novels, err := s.Store.ListOwnedNovelsWithURL(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to list novels", err)
		}
		if len(novels) == 0 {
			return e.JSON(http.StatusOK, store.BatchCheckResponse{
				Results: []store.BatchCheckNovelResult{},
				Checked: 0, WithUpdates: 0, Errors: 0,
			})
		}
		dl := s.DownloaderFactory()
		supported := make([]store.Novel, 0, len(novels))
		for _, n := range novels {
			if dl.IsSupportedURL(n.URL) {
				supported = append(supported, n)
			}
		}
		if len(supported) == 0 {
			return e.JSON(http.StatusOK, store.BatchCheckResponse{
				Results: []store.BatchCheckNovelResult{},
				Checked: 0, WithUpdates: 0, Errors: 0,
			})
		}
		results := make([]store.BatchCheckNovelResult, 0, len(supported))
		checked := 0
		withUpdates := 0
		errCount := 0
		for i, novel := range supported {
			if i > 0 {
				if err := dl.SleepBetweenChapters(e.Request.Context()); err != nil {
					break
				}
			}
			info, err := dl.GetNovelInfo(e.Request.Context(), novel.URL)
			if err != nil {
				errCount++
				results = append(results, store.BatchCheckNovelResult{
					NovelID: novel.ID, SourceTitle: novel.SourceTitle,
					Error: err.Error(),
				})
				continue
			}
			maxOrder, err := s.Store.GetMaxChapterOrder(e.Auth.Id, novel.ID)
			if err != nil {
				errCount++
				results = append(results, store.BatchCheckNovelResult{
					NovelID: novel.ID, SourceTitle: novel.SourceTitle,
					Error: err.Error(),
				})
				continue
			}
			existingTitles, err := s.Store.GetExistingChapterURLs(e.Auth.Id, novel.ID)
			if err != nil {
				errCount++
				results = append(results, store.BatchCheckNovelResult{
					NovelID: novel.ID, SourceTitle: novel.SourceTitle,
					Error: err.Error(),
				})
				continue
			}
			newCh := make([]store.DownloadChapterInfo, 0)
			newAvailable := 0
			firstNew := 0
			lastNew := 0
			startOrder := 0
			for srcIdx, ch := range info.Chapters {
				chNum := extractChapterOrder(ch.Title)
				if chNum > 0 && chNum <= maxOrder {
					continue
				}
				if existingTitles[ch.Title] {
					continue
				}
				newAvailable++
				pos := chNum
				if pos <= 0 {
					pos = srcIdx + 1
				}
				if startOrder == 0 {
					startOrder = pos
				}
				if chNum > 0 {
					if firstNew == 0 || chNum < firstNew {
						firstNew = chNum
					}
					if chNum > lastNew {
						lastNew = chNum
					}
				}
				chTitle := ch.Title
				if chTitle == "" {
					chTitle = fmt.Sprintf("Capítulo %d", pos)
				}
				newCh = append(newCh, store.DownloadChapterInfo{
					URL:   ch.URL,
					Title: chTitle,
				})
			}
			checked++
			if newAvailable > 0 {
				withUpdates++
			}
			if newAvailable == 0 {
				continue
			}
			results = append(results, store.BatchCheckNovelResult{
				NovelID:         novel.ID,
				SourceTitle:     novel.SourceTitle,
				SourceAuthor:    novel.SourceAuthor,
				CoverURL:        info.CoverURL,
				NewChapters:     newAvailable,
				FirstNewChapter: firstNew,
				LastNewChapter:  lastNew,
				StartOrder:      startOrder,
				CurrentChapters: len(existingTitles),
				TotalChapters:   len(info.Chapters),
				NewChapterInfo:  newCh,
			})
		}
		return e.JSON(http.StatusOK, store.BatchCheckResponse{
			Results: results, Checked: checked,
			WithUpdates: withUpdates, Errors: errCount,
		})
	})
	api.POST("/db/novels/batch-update-from-url", func(e *core.RequestEvent) error {
		body := struct {
			Selections []store.BatchUpdateSelection `json:"selections"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if len(body.Selections) == 0 {
			return e.BadRequestError("selections required", nil)
		}
		jobs := make([]store.BatchUpdateJobResult, 0, len(body.Selections))
		totalPending := 0
		for _, sel := range body.Selections {
			novel, err := s.Store.GetOwnedNovel(e.Auth.Id, sel.NovelID)
			if err != nil {
				continue
			}
			chaptersToDownload := sel.NewChapterInfo
			if sel.StartChapter > 0 || sel.EndChapter > 0 {
				filtered := make([]store.DownloadChapterInfo, 0)
				for _, ch := range sel.NewChapterInfo {
					order := extractChapterOrder(ch.Title)
					if order <= 0 {
						order = sel.StartOrder + len(filtered)
					}
					if sel.StartChapter > 0 && order < sel.StartChapter {
						continue
					}
					if sel.EndChapter > 0 && order > sel.EndChapter {
						continue
					}
					filtered = append(filtered, ch)
				}
				chaptersToDownload = filtered
			}
			if len(chaptersToDownload) == 0 {
				continue
			}
			firstOrder := extractChapterOrder(chaptersToDownload[0].Title)
			if firstOrder <= 0 {
				firstOrder = sel.StartOrder
			}
			optionsJSON, _ := json.Marshal(map[string]any{
				"url":            novel.URL,
				"chapters":       chaptersToDownload,
				"startOrder":     firstOrder,
				"sourceLanguage": novel.SourceLanguage,
				"targetLanguage": novel.TargetLanguage,
			})
			job := &store.Job{
				NovelID:       sel.NovelID,
				Status:        "pending",
				Operation:     "download",
				ChapterIDs:    "[]",
				OptionsJSON:   string(optionsJSON),
				TotalChapters: len(chaptersToDownload),
			}
			if err := s.Store.CreateJob(e.Auth.Id, job); err != nil {
				continue
			}
			s.enqueueJob(job.ID)
			jobs = append(jobs, store.BatchUpdateJobResult{
				NovelID:         sel.NovelID,
				JobID:           job.ID,
				PendingChapters: len(chaptersToDownload),
			})
			totalPending += len(chaptersToDownload)
		}
		return e.JSON(http.StatusOK, store.BatchUpdateResponse{
			Jobs: jobs, TotalPending: totalPending,
		})
	})
	api.GET("/db/novels/batch-translate-preview", func(e *core.RequestEvent) error {
		novels, err := s.Store.ListOwnedNovelsWithTranslationStats(e.Auth.Id)
		if err != nil {
			return e.InternalServerError("failed to list novels", err)
		}
		results := make([]store.BatchTranslateNovelResult, 0, len(novels))
		withPending := 0
		for _, novel := range novels {
			pendingChapters := novel.ChapterCount - novel.TranslatedCount
			if pendingChapters < 0 {
				pendingChapters = 0
			}
			hasOriginal := novel.OriginalCharCount > 0
			result := store.BatchTranslateNovelResult{
				NovelID:            novel.ID,
				SourceTitle:        novel.SourceTitle,
				SourceAuthor:       novel.SourceAuthor,
				CoverURL:           novel.CoverPath,
				PendingChapters:    pendingChapters,
				TotalChapters:      novel.ChapterCount,
				TranslatedCount:    novel.TranslatedCount,
				CompletedCount:     novel.CompletedCount,
				HasOriginalContent: hasOriginal,
			}
			if pendingChapters > 0 {
				withPending++
				results = append(results, result)
			}
		}
		return e.JSON(http.StatusOK, store.BatchTranslateResponse{
			Results:     results,
			TotalNovels: len(results),
			WithPending: withPending,
		})
	})
	api.POST("/db/novels/batch-translate", func(e *core.RequestEvent) error {
		body := struct {
			Selections []store.BatchTranslateSelection `json:"selections"`
		}{}
		if err := e.BindBody(&body); err != nil {
			return e.BadRequestError("invalid body", err)
		}
		if len(body.Selections) == 0 {
			return e.BadRequestError("selections required", nil)
		}
		jobs := make([]store.BatchTranslateJobResult, 0, len(body.Selections))
		totalPending := 0
		for _, sel := range body.Selections {
			novel, err := s.Store.GetOwnedNovel(e.Auth.Id, sel.NovelID)
			if err != nil {
				continue
			}
			var chapterIDs []string
			if len(sel.ChapterIDs) > 0 {
				chapterIDs = sel.ChapterIDs
			} else {
				pending, err := s.Store.GetOwnedNovelChapterIDsByStatus(e.Auth.Id, sel.NovelID)
				if err != nil || len(pending) == 0 {
					continue
				}
				chapterIDs = pending
			}
			idsJSON, _ := json.Marshal(chapterIDs)
			job := &store.Job{
				NovelID:       sel.NovelID,
				Status:        "pending",
				Operation:     "translate",
				ChapterIDs:    string(idsJSON),
				TotalChapters: len(chapterIDs),
			}
			if err := s.Store.CreateJob(e.Auth.Id, job); err != nil {
				continue
			}
			if chapters, _, err := s.Store.LoadJobChapters(job); err == nil {
				chIDs := make([]string, 0, len(chapters))
				for _, chapter := range chapters {
					chIDs = append(chIDs, chapter.ID)
				}
				_ = s.Store.UpdateChaptersStatusFast(chIDs, "processing", "")
			}
			s.enqueueJob(job.ID)
			jobs = append(jobs, store.BatchTranslateJobResult{
				NovelID:         sel.NovelID,
				JobID:           job.ID,
				PendingChapters: len(chapterIDs),
			})
			totalPending += len(chapterIDs)
			_ = novel
		}
		return e.JSON(http.StatusOK, store.BatchTranslateStartResponse{
			Jobs: jobs, TotalPending: totalPending,
		})
	})
}

func detectZipRoot(entries []struct {
	name    string
	content []byte
}) string {
	if len(entries) == 0 {
		return ""
	}
	candidate := entries[0].name
	for {
		idx := strings.IndexByte(candidate, '/')
		if idx < 0 {
			return ""
		}
		prefix := candidate[:idx+1]
		allMatch := true
		for _, e := range entries {
			if !strings.HasPrefix(e.name, prefix) {
				allMatch = false
				break
			}
		}
		if allMatch {
			if hasFileAtRoot(strings.TrimSuffix(prefix, "/"), entries) {
				return prefix
			}
			candidate = entries[0].name[idx+1:]
			continue
		}
		return ""
	}
}

func hasFileAtRoot(dir string, entries []struct {
	name    string
	content []byte
}) bool {
	for _, e := range entries {
		rest := strings.TrimPrefix(e.name, dir+"/")
		if rest != "" && strings.IndexByte(rest, '/') < 0 {
			if base := strings.ToLower(filepath.Base(rest)); base == "metadata.json" || strings.HasPrefix(base, "originals") || strings.HasPrefix(base, "translated") {
				return true
			}
		}
	}
	return false
}

func extractChapterOrder(filename string) int {
	matches := chapterOrderRegex.FindStringSubmatch(filename)
	if len(matches) >= 2 {
		if n, err := strconv.Atoi(matches[1]); err == nil {
			return n
		}
	}
	return 0
}

func extractChapterTitle(content, filename string) string {
	first, _, _ := strings.Cut(strings.TrimSpace(content), "\n")
	first = strings.TrimSpace(first)
	first = strings.TrimLeft(first, "# ")
	first = stripMarkdown(first)
	first = strings.TrimSpace(first)
	if first != "" {
		return first
	}
	return filename
}

func stripMarkdown(s string) string {
	s = strings.ReplaceAll(s, "***", "")
	s = strings.ReplaceAll(s, "**", "")
	s = strings.ReplaceAll(s, "__", "")
	s = strings.ReplaceAll(s, "*", "")
	s = strings.ReplaceAll(s, "~~", "")
	s = strings.ReplaceAll(s, "`", "")
	return s
}

func contentAfterTitle(content string) string {
	_, rest, found := strings.Cut(strings.TrimSpace(content), "\n")
	if !found || rest == "" {
		return strings.TrimSpace(content)
	}
	return strings.TrimSpace(rest)
}
