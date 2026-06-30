package api

import (
	"bytes"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/pocketbase/pocketbase"
	"translator-server/internal/config"
	"translator-server/internal/secure"
	"translator-server/internal/store"
)

type apiTestEnv struct {
	handler http.Handler
	store   *store.Store
	server  *Server
}

type authPayload struct {
	Token string     `json:"token"`
	User  store.User `json:"user"`
}

type novelPayload struct {
	ID          string `json:"id"`
	OwnerID     string `json:"ownerId"`
	SourceTitle string `json:"sourceTitle"`
	IsPublic    bool   `json:"isPublic"`
}

type chapterPayload struct {
	ID                string `json:"id"`
	NovelID           string `json:"novelId"`
	ChapterOrder      int    `json:"chapterOrder"`
	Title             string `json:"title"`
	TranslatedTitle   string `json:"translatedTitle"`
	OriginalContent   string `json:"originalContent"`
	TranslatedContent string `json:"translatedContent"`
	RefinedContent    string `json:"refinedContent"`
	Status            string `json:"status"`
	ErrorMessage      string `json:"errorMessage"`
}

type jobPayload struct {
	ID     string `json:"id"`
	Status string `json:"status"`
}

type activeJobStatusPayload struct {
	HasActive bool `json:"hasActive"`
}

type providersPayload struct {
	Providers []store.ProviderSetting `json:"providers"`
}

func TestAuthRegisterAndFetchMe(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice@example.com", "secret123", "Alice")

	resp := doJSONRequest(t, env.handler, http.MethodGet, "/api/auth/me", alice.Token, nil)
	assertStatus(t, resp, http.StatusOK)

	var me authPayload
	decodeResponse(t, resp, &me)
	if me.User.ID == "" {
		t.Fatalf("expected user id in /me response")
	}
	if me.User.Email != "alice@example.com" {
		t.Fatalf("expected email alice@example.com, got %q", me.User.Email)
	}
	if me.User.Theme != "system" {
		t.Fatalf("expected default theme system, got %q", me.User.Theme)
	}
}

func TestNovelResponseIncludesOwnerIDAndChapterStatusRequiresOwnership(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice@example.com", "secret123", "Alice")
	bob := registerUser(t, env.handler, "bob@example.com", "secret123", "Bob")

	novelResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels", alice.Token, map[string]any{
		"sourceTitle":    "Mi novela",
		"sourceLanguage": "es",
		"targetLanguage": "en",
	})
	assertStatus(t, novelResp, http.StatusCreated)

	var novel novelPayload
	decodeResponse(t, novelResp, &novel)
	if novel.OwnerID != alice.User.ID {
		t.Fatalf("expected ownerId %q, got %q", alice.User.ID, novel.OwnerID)
	}

	chapterResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/chapters", alice.Token, map[string]any{
		"chapterOrder":    1,
		"title":           "Capítulo 1",
		"originalContent": "Hola mundo",
	})
	assertStatus(t, chapterResp, http.StatusCreated)

	var chapter chapterPayload
	decodeResponse(t, chapterResp, &chapter)

	forbiddenResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID+"/status", bob.Token, map[string]any{
		"status":       "failed",
		"errorMessage": "intrusion",
	})
	assertStatus(t, forbiddenResp, http.StatusForbidden)

	okResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID+"/status", alice.Token, map[string]any{
		"status":       "processing",
		"errorMessage": "",
	})
	assertStatus(t, okResp, http.StatusOK)

	decodeResponse(t, okResp, &chapter)
	if chapter.Status != "processing" {
		t.Fatalf("expected chapter status processing, got %q", chapter.Status)
	}
}

func TestChapterUpsertPreservesStatusWhenOmitted(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-preserve-status@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Estado", "es", "en")
	chapter := createChapter(t, env.handler, alice.Token, novel.ID, 1)

	statusResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID+"/status", alice.Token, map[string]any{
		"status":       "translated",
		"errorMessage": "",
	})
	assertStatus(t, statusResp, http.StatusOK)

	updateResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/chapters", alice.Token, map[string]any{
		"id":                chapter.ID,
		"chapterOrder":      1,
		"title":             "Capítulo 1 editado",
		"originalContent":   "Texto original",
		"translatedContent": "Texto traducido manual",
	})
	assertStatus(t, updateResp, http.StatusCreated)

	var updatedChapter chapterPayload
	decodeResponse(t, updateResp, &updatedChapter)
	if updatedChapter.Status != "translated" {
		t.Fatalf("expected chapter status translated after manual save, got %q", updatedChapter.Status)
	}
}

func TestImportEpubPersistsCoverFile(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-cover@example.com", "secret123", "Alice")

	blob, err := os.ReadFile(filepath.Join("..", "..", "test", "epub.epub"))
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	fileWriter, err := writer.CreateFormFile("file", "test.epub")
	if err != nil {
		t.Fatalf("create form file: %v", err)
	}
	if _, err := fileWriter.Write(blob); err != nil {
		t.Fatalf("write file: %v", err)
	}
	if err := writer.WriteField("sourceLanguage", "en"); err != nil {
		t.Fatalf("write source: %v", err)
	}
	if err := writer.WriteField("targetLanguage", "es"); err != nil {
		t.Fatalf("write target: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close writer: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/db/novels/import-epub", &body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+alice.Token)

	rec := httptest.NewRecorder()
	env.handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected status 201, got %d: %s", rec.Code, rec.Body.String())
	}

	var importResp struct {
		Novel map[string]any `json:"novel"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &importResp); err != nil {
		t.Fatalf("decode import response: %v", err)
	}
	coverPath, _ := importResp.Novel["coverPath"].(string)
	if coverPath == "" {
		t.Fatalf("expected coverPath in novel response, got %v", importResp.Novel["coverPath"])
	}

	coverReq := httptest.NewRequest(http.MethodGet, coverPath, nil)
	coverRec := httptest.NewRecorder()
	env.handler.ServeHTTP(coverRec, coverReq)
	if coverRec.Code != http.StatusOK {
		t.Fatalf("expected cover response 200, got %d: %s", coverRec.Code, coverRec.Body.String())
	}
	coverBody, err := io.ReadAll(coverRec.Body)
	if err != nil {
		t.Fatalf("read cover body: %v", err)
	}
	if len(coverBody) == 0 {
		t.Fatal("expected non-empty cover body")
	}
}

func TestListNovelsSortByCreatedSucceeds(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-sort@example.com", "secret123", "Alice")
	createNovel(t, env.handler, alice.Token, "Ordenable", "en", "es")

	resp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels", alice.Token, nil)
	assertStatus(t, resp, http.StatusOK)

	var listResp struct {
		Items []map[string]any `json:"items"`
	}
	decodeResponse(t, resp, &listResp)
	if len(listResp.Items) != 1 {
		t.Fatalf("expected 1 novel in list, got %d", len(listResp.Items))
	}
}

func TestImportedCoverIsPubliclyFetchable(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-public-cover@example.com", "secret123", "Alice")
	bob := registerUser(t, env.handler, "bob-public-cover@example.com", "secret123", "Bob")

	blob, err := os.ReadFile(filepath.Join("..", "..", "test", "epub.epub"))
	if err != nil {
		t.Skip("test epub not found:", err)
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	fileWriter, err := writer.CreateFormFile("file", "test.epub")
	if err != nil {
		t.Fatalf("create form file: %v", err)
	}
	if _, err := fileWriter.Write(blob); err != nil {
		t.Fatalf("write file: %v", err)
	}
	if err := writer.WriteField("sourceLanguage", "en"); err != nil {
		t.Fatalf("write source: %v", err)
	}
	if err := writer.WriteField("targetLanguage", "es"); err != nil {
		t.Fatalf("write target: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close writer: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/db/novels/import-epub", &body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+alice.Token)

	rec := httptest.NewRecorder()
	env.handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected status 201, got %d: %s", rec.Code, rec.Body.String())
	}

	var importResp struct {
		Novel struct {
			CoverPath string `json:"coverPath"`
			ID        string `json:"id"`
		} `json:"novel"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &importResp); err != nil {
		t.Fatalf("decode import response: %v", err)
	}
	if importResp.Novel.CoverPath == "" {
		t.Fatalf("expected coverPath in novel response, got %v", rec.Body.String())
	}

	ownerReq := httptest.NewRequest(http.MethodGet, importResp.Novel.CoverPath, nil)
	ownerRec := httptest.NewRecorder()
	env.handler.ServeHTTP(ownerRec, ownerReq)
	if ownerRec.Code != http.StatusOK {
		t.Fatalf("expected cover response 200 for owner, got %d: %s", ownerRec.Code, ownerRec.Body.String())
	}

	_ = bob
}

func TestImportEpubWithLongDescriptionSucceeds(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-longdesc@example.com", "secret123", "Alice")

	matches, err := filepath.Glob(filepath.Join("..", "..", "test", "*.epub"))
	if err != nil {
		t.Fatalf("glob epubs: %v", err)
	}
	if len(matches) == 0 {
		t.Skip("no epubs in test/ directory")
	}

	var (
		blob       []byte
		uploadName string
	)
	for _, m := range matches {
		b, err := os.ReadFile(m)
		if err != nil {
			continue
		}
		blob = b
		uploadName = filepath.Base(m)
		break
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)
	fileWriter, err := writer.CreateFormFile("file", uploadName)
	if err != nil {
		t.Fatalf("create form file: %v", err)
	}
	if _, err := fileWriter.Write(blob); err != nil {
		t.Fatalf("write file: %v", err)
	}
	if err := writer.WriteField("sourceLanguage", "en"); err != nil {
		t.Fatalf("write source: %v", err)
	}
	if err := writer.WriteField("targetLanguage", "es"); err != nil {
		t.Fatalf("write target: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close writer: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/api/db/novels/import-epub", &body)
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+alice.Token)

	rec := httptest.NewRecorder()
	env.handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected status 201, got %d: %s", rec.Code, rec.Body.String())
	}

	var importResp struct {
		Novel map[string]any `json:"novel"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &importResp); err != nil {
		t.Fatalf("decode import response: %v", err)
	}
	for _, key := range []string{"sourceTitle", "sourceAuthor", "sourceDescription"} {
		if _, ok := importResp.Novel[key]; !ok {
			t.Fatalf("expected %q in novel response, got %v", key, importResp.Novel)
		}
	}
}

func TestActiveJobStatusAndCreatedJobMarksChapterProcessing(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-active-job@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Trabajo activo", "es", "en")
	chapter := createChapter(t, env.handler, alice.Token, novel.ID, 1)

	chapterIDsJSON, err := json.Marshal([]string{chapter.ID})
	if err != nil {
		t.Fatalf("marshal chapter ids: %v", err)
	}
	activeJob := &store.Job{
		NovelID:       novel.ID,
		Status:        "pending",
		Operation:     "translate",
		ChapterIDs:    string(chapterIDsJSON),
		TotalChapters: 1,
	}
	if err := env.store.CreateJob(alice.User.ID, activeJob); err != nil {
		t.Fatalf("create active job: %v", err)
	}

	statusResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/translation-jobs/active/status", alice.Token, nil)
	assertStatus(t, statusResp, http.StatusOK)

	var activeStatus activeJobStatusPayload
	decodeResponse(t, statusResp, &activeStatus)
	if !activeStatus.HasActive {
		t.Fatal("expected hasActive=true when user has a pending job")
	}

	jobResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/translation-jobs", alice.Token, map[string]any{
		"chapterIds": []string{chapter.ID},
		"operation":  "translate",
		"options": map[string]any{
			"provider": "venice",
			"model":    "deepseek-v4-flash",
		},
	})
	assertStatus(t, jobResp, http.StatusCreated)

	chapterResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID, alice.Token, nil)
	assertStatus(t, chapterResp, http.StatusOK)

	var updatedChapter chapterPayload
	decodeResponse(t, chapterResp, &updatedChapter)
	if updatedChapter.Status != "processing" {
		t.Fatalf("expected job creation to mark chapter processing, got %q", updatedChapter.Status)
	}
}

func TestJobPatchRequiresOwner(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice@example.com", "secret123", "Alice")
	bob := registerUser(t, env.handler, "bob@example.com", "secret123", "Bob")

	novel := createNovel(t, env.handler, alice.Token, "Trabajo", "es", "en")
	chapter := createChapter(t, env.handler, alice.Token, novel.ID, 1)

	jobResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/translation-jobs", alice.Token, map[string]any{
		"chapterIds": []string{chapter.ID},
		"operation":  "translate",
		"options": map[string]any{
			"provider": "venice",
			"model":    "deepseek-v4-flash",
		},
	})
	assertStatus(t, jobResp, http.StatusCreated)

	var job jobPayload
	decodeResponse(t, jobResp, &job)

	forbiddenResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/translation-jobs/"+job.ID, bob.Token, map[string]any{
		"status": "cancelled",
	})
	assertStatus(t, forbiddenResp, http.StatusForbidden)

	processingResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID+"/status", alice.Token, map[string]any{
		"status":       "processing",
		"errorMessage": "",
	})
	assertStatus(t, processingResp, http.StatusOK)

	okResp := doJSONRequest(t, env.handler, http.MethodPatch, "/api/db/translation-jobs/"+job.ID, alice.Token, map[string]any{
		"status": "cancelled",
	})
	assertStatus(t, okResp, http.StatusOK)

	decodeResponse(t, okResp, &job)
	if job.Status != "cancelled" {
		t.Fatalf("expected job status cancelled, got %q", job.Status)
	}

	chapterResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID, alice.Token, nil)
	assertStatus(t, chapterResp, http.StatusOK)

	var updatedChapter chapterPayload
	decodeResponse(t, chapterResp, &updatedChapter)
	if updatedChapter.Status != "pending" {
		t.Fatalf("expected cancelled job chapter to reset to pending, got %q", updatedChapter.Status)
	}
}

func TestDeleteChapterRemovesJobReferencesAndUpdatesStats(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-delete-chapter@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Novela", "es", "en")
	chapter1 := createChapter(t, env.handler, alice.Token, novel.ID, 1)
	chapter2 := createChapter(t, env.handler, alice.Token, novel.ID, 2)

	chapterIDsJSON, err := json.Marshal([]string{chapter1.ID, chapter2.ID})
	if err != nil {
		t.Fatalf("marshal chapter ids: %v", err)
	}
	job := &store.Job{
		NovelID:                 novel.ID,
		Status:                  "pending",
		Operation:               "translate",
		ChapterIDs:              string(chapterIDsJSON),
		TotalChapters:           2,
		AutoSegmentChapterID:    chapter1.ID,
		AutoSegmentChapterTitle: "Capítulo",
	}
	if err := env.store.CreateJob(alice.User.ID, job); err != nil {
		t.Fatalf("create job: %v", err)
	}

	deleteResp := doJSONRequest(t, env.handler, http.MethodDelete, "/api/db/novels/"+novel.ID+"/chapters/"+chapter1.ID, alice.Token, nil)
	assertStatus(t, deleteResp, http.StatusOK)

	deletedChapterResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/chapters/"+chapter1.ID, alice.Token, nil)
	assertStatus(t, deletedChapterResp, http.StatusNotFound)

	updatedJob, err := env.store.GetOwnedJob(alice.User.ID, job.ID)
	if err != nil {
		t.Fatalf("get updated job: %v", err)
	}
	var updatedIDs []string
	if err := json.Unmarshal([]byte(updatedJob.ChapterIDs), &updatedIDs); err != nil {
		t.Fatalf("decode updated job chapter ids: %v", err)
	}
	if len(updatedIDs) != 1 || updatedIDs[0] != chapter2.ID {
		t.Fatalf("expected job to keep only surviving chapter id %q, got %#v", chapter2.ID, updatedIDs)
	}
	if updatedJob.AutoSegmentChapterID != "" || updatedJob.AutoSegmentChapterTitle != "" {
		t.Fatalf("expected auto segment refs cleared after chapter delete, got id=%q title=%q", updatedJob.AutoSegmentChapterID, updatedJob.AutoSegmentChapterTitle)
	}
	if updatedJob.TotalChapters != 1 {
		t.Fatalf("expected pending job total chapters to shrink to 1, got %d", updatedJob.TotalChapters)
	}

	stats, err := env.store.GetChapterStatsAccessible(alice.User.ID, novel.ID)
	if err != nil {
		t.Fatalf("get chapter stats: %v", err)
	}
	if stats.TotalChapters != 1 {
		t.Fatalf("expected chapter_count=1 after delete, got %d", stats.TotalChapters)
	}
}

func TestDeleteNovelCascadesRelatedRecords(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-delete-novel@example.com", "secret123", "Alice")

	imported, err := env.store.ImportEpubNovel(&store.ImportEpubNovelInput{
		OwnerID:        alice.User.ID,
		FileName:       "novela.epub",
		FileBlob:       []byte("fake-epub"),
		MimeType:       "application/epub+zip",
		SourceTitle:    "Novela completa",
		SourceLanguage: "es",
		TargetLanguage: "en",
		CoverMime:      "image/png",
		CoverBlob:      []byte("fake-cover"),
		Chapters: []store.ImportedEpubChapter{
			{Title: "Capítulo 1", Content: "Texto 1"},
			{Title: "Capítulo 2", Content: "Texto 2"},
		},
	})
	if err != nil {
		t.Fatalf("import novel: %v", err)
	}
	chapters, err := env.store.ListChaptersAccessible(alice.User.ID, imported.Novel.ID)
	if err != nil {
		t.Fatalf("list chapters: %v", err)
	}
	if len(chapters) != 2 {
		t.Fatalf("expected 2 chapters after import, got %d", len(chapters))
	}
	chapterIDs := []string{chapters[0].ID, chapters[1].ID}
	chapterIDsJSON, err := json.Marshal(chapterIDs)
	if err != nil {
		t.Fatalf("marshal chapter ids: %v", err)
	}
	job := &store.Job{NovelID: imported.Novel.ID, Status: "pending", Operation: "translate", ChapterIDs: string(chapterIDsJSON), TotalChapters: len(chapterIDs)}
	if err := env.store.CreateJob(alice.User.ID, job); err != nil {
		t.Fatalf("create job: %v", err)
	}

	deleteResp := doJSONRequest(t, env.handler, http.MethodDelete, "/api/db/novels/"+imported.Novel.ID, alice.Token, nil)
	assertStatus(t, deleteResp, http.StatusOK)

	novelResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+imported.Novel.ID, alice.Token, nil)
	assertStatus(t, novelResp, http.StatusNotFound)

	chapterRecords, err := env.store.App.FindRecordsByFilter(store.ChaptersCollection, "novel = {:novel}", "", 10, 0, map[string]any{"novel": imported.Novel.ID})
	if err != nil {
		t.Fatalf("find chapter records: %v", err)
	}
	if len(chapterRecords) != 0 {
		t.Fatalf("expected no chapter records after novel delete, got %d", len(chapterRecords))
	}

	jobRecords, err := env.store.App.FindRecordsByFilter(store.JobsCollection, "novel = {:novel}", "", 10, 0, map[string]any{"novel": imported.Novel.ID})
	if err != nil {
		t.Fatalf("find job records: %v", err)
	}
	if len(jobRecords) != 0 {
		t.Fatalf("expected no job records after novel delete, got %d", len(jobRecords))
	}

	epubRecords, err := env.store.App.FindRecordsByFilter(store.EpubsCollection, "novel = {:novel}", "", 10, 0, map[string]any{"novel": imported.Novel.ID})
	if err != nil {
		t.Fatalf("find epub records: %v", err)
	}
	if len(epubRecords) != 0 {
		t.Fatalf("expected no epub records after novel delete, got %d", len(epubRecords))
	}

	if imported.Novel.CoverPath != "" {
		coverResp := doJSONRequest(t, env.handler, http.MethodGet, imported.Novel.CoverPath, "", nil)
		assertStatus(t, coverResp, http.StatusNotFound)
	}
}

func TestProviderAPIKeysAreWriteOnlyAndRevocable(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice@example.com", "secret123", "Alice")
	secret := "super-secret-api-key"

	replaceResp := doJSONRequest(t, env.handler, http.MethodPut, "/api/user/providers/venice/key", alice.Token, map[string]any{
		"apiKey": secret,
	})
	assertStatus(t, replaceResp, http.StatusOK)
	body := readBody(t, replaceResp)
	if strings.Contains(body, secret) {
		t.Fatalf("provider key leaked in replace response: %s", body)
	}

	listResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/user/providers", alice.Token, nil)
	assertStatus(t, listResp, http.StatusOK)
	listBody := readBody(t, listResp)
	if strings.Contains(listBody, secret) {
		t.Fatalf("provider key leaked in list response: %s", listBody)
	}

	var providers providersPayload
	decodeStringResponse(t, listBody, &providers)
	venice := findProvider(t, providers.Providers, "venice")
	if !venice.APIKeyConfigured {
		t.Fatalf("expected venice api key to be marked configured")
	}
	if venice.APIKeyUpdatedAt == "" {
		t.Fatalf("expected venice api key updated timestamp")
	}

	deleteResp := doJSONRequest(t, env.handler, http.MethodDelete, "/api/user/providers/venice/key", alice.Token, nil)
	assertStatus(t, deleteResp, http.StatusNoContent)

	resolved, err := env.store.ResolveProviderAISettings(alice.User.ID, "venice")
	if err != nil {
		t.Fatalf("resolve provider settings: %v", err)
	}
	if resolved.APIKey != "" {
		t.Fatalf("expected resolved api key to be empty after delete, got %q", resolved.APIKey)
	}

	finalResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/user/providers", alice.Token, nil)
	assertStatus(t, finalResp, http.StatusOK)
	var finalProviders providersPayload
	decodeResponse(t, finalResp, &finalProviders)
	venice = findProvider(t, finalProviders.Providers, "venice")
	if venice.APIKeyConfigured {
		t.Fatalf("expected venice api key to be unconfigured after delete")
	}
}

func TestProviderConfiguredTimeoutMsIsRespected(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice@example.com", "secret123", "Alice")

	updateResp := doJSONRequest(t, env.handler, http.MethodPut, "/api/user/providers/venice", alice.Token, map[string]any{
		"model":     "deepseek-v4-flash",
		"baseUrl":   "https://api.venice.ai/api/v1",
		"timeoutMs": 600000,
	})
	assertStatus(t, updateResp, http.StatusOK)

	resolved, err := env.store.ResolveProviderAISettings(alice.User.ID, "venice")
	if err != nil {
		t.Fatalf("resolve provider settings: %v", err)
	}
	if resolved.TimeoutMs != 600000 {
		t.Fatalf("expected resolved TimeoutMs=600000 (user-configured), got %d", resolved.TimeoutMs)
	}

	clearResp := doJSONRequest(t, env.handler, http.MethodPut, "/api/user/providers/venice", alice.Token, map[string]any{
		"model":     "deepseek-v4-flash",
		"baseUrl":   "https://api.venice.ai/api/v1",
		"timeoutMs": 0,
	})
	assertStatus(t, clearResp, http.StatusOK)

	defaultResolved, err := env.store.ResolveProviderAISettings(alice.User.ID, "venice")
	if err != nil {
		t.Fatalf("resolve provider settings: %v", err)
	}
	if defaultResolved.TimeoutMs != store.DefaultAISettings.TimeoutMs {
		t.Fatalf("expected resolved TimeoutMs to fall back to default %d when unset, got %d", store.DefaultAISettings.TimeoutMs, defaultResolved.TimeoutMs)
	}
}

func newAPITestEnv(t *testing.T) *apiTestEnv {
	t.Helper()

	dataDir := t.TempDir()
	app := pocketbase.NewWithConfig(pocketbase.Config{DefaultDataDir: dataDir})
	if err := app.Bootstrap(); err != nil {
		t.Fatalf("bootstrap pocketbase: %v", err)
	}

	encryptor, err := secure.NewEncryptorFromConfig("", filepath.Join(dataDir, "app.key"))
	if err != nil {
		t.Fatalf("create encryptor: %v", err)
	}

	st := store.New(app, encryptor)
	if err := st.EnsureSchema(); err != nil {
		t.Fatalf("ensure schema: %v", err)
	}

	server := New(st, &config.Config{DataDir: dataDir})
	return &apiTestEnv{handler: Router(server), store: st, server: server}
}

func registerUser(t *testing.T, handler http.Handler, email, password, name string) authPayload {
	t.Helper()
	resp := doJSONRequest(t, handler, http.MethodPost, "/api/auth/register", "", map[string]any{
		"email":    email,
		"password": password,
		"name":     name,
	})
	assertStatus(t, resp, http.StatusCreated)
	var out authPayload
	decodeResponse(t, resp, &out)
	if out.Token == "" {
		t.Fatalf("expected auth token for %s", email)
	}
	return out
}

func createNovel(t *testing.T, handler http.Handler, token, title, sourceLanguage, targetLanguage string) novelPayload {
	t.Helper()
	resp := doJSONRequest(t, handler, http.MethodPost, "/api/db/novels", token, map[string]any{
		"sourceTitle":    title,
		"sourceLanguage": sourceLanguage,
		"targetLanguage": targetLanguage,
	})
	assertStatus(t, resp, http.StatusCreated)
	var novel novelPayload
	decodeResponse(t, resp, &novel)
	return novel
}

func TestCleanOnlyOriginalsPreservesOtherFields(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-clean@example.com", "secret123", "Alice")

	novel := createNovel(t, env.handler, alice.Token, "Limpieza", "es", "en")
	resp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/chapters", alice.Token, map[string]any{
		"chapterOrder":      1,
		"title":             "Título Original",
		"translatedTitle":   "Translated Title",
		"originalContent":   "línea uno\nlínea dos\nBORRAR DESPUÉS\nlínea tres",
		"translatedContent": "translated one\ntranslated two\ntranslated three",
		"refinedContent":    "refined one\nrefined two\nrefined three",
	})
	assertStatus(t, resp, http.StatusCreated)
	var chapter chapterPayload
	decodeResponse(t, resp, &chapter)

	cleanResp := doJSONRequest(t, env.handler, http.MethodPost, "/api/db/novels/"+novel.ID+"/chapters/clean", alice.Token, map[string]any{
		"chapterIds": []string{chapter.ID},
		"mode":       "remove_after",
		"searchText": "BORRAR",
		"applyTo":    "original",
	})
	assertStatus(t, cleanResp, http.StatusOK)

	fetchResp := doJSONRequest(t, env.handler, http.MethodGet, "/api/db/novels/"+novel.ID+"/chapters/"+chapter.ID, alice.Token, nil)
	assertStatus(t, fetchResp, http.StatusOK)
	var updated chapterPayload
	decodeResponse(t, fetchResp, &updated)

	if updated.OriginalContent != "línea uno\nlínea dos" {
		t.Fatalf("original content not cleaned as expected, got %q", updated.OriginalContent)
	}
	if updated.TranslatedContent != "translated one\ntranslated two\ntranslated three" {
		t.Fatalf("translated content was overwritten, got %q", updated.TranslatedContent)
	}
	if updated.RefinedContent != "refined one\nrefined two\nrefined three" {
		t.Fatalf("refined content was overwritten, got %q", updated.RefinedContent)
	}
	if updated.Title != "Título Original" {
		t.Fatalf("title was overwritten, got %q", updated.Title)
	}
	if updated.TranslatedTitle != "Translated Title" {
		t.Fatalf("translated title was overwritten, got %q", updated.TranslatedTitle)
	}
}

func createChapter(t *testing.T, handler http.Handler, token, novelID string, order int) chapterPayload {
	t.Helper()
	resp := doJSONRequest(t, handler, http.MethodPost, "/api/db/novels/"+novelID+"/chapters", token, map[string]any{
		"chapterOrder":    order,
		"title":           "Capítulo",
		"originalContent": "Texto original",
	})
	assertStatus(t, resp, http.StatusCreated)
	var chapter chapterPayload
	decodeResponse(t, resp, &chapter)
	return chapter
}

func doJSONRequest(t *testing.T, handler http.Handler, method, path, token string, body any) *httptest.ResponseRecorder {
	t.Helper()

	var payload []byte
	if body != nil {
		var err error
		payload, err = json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal request body: %v", err)
		}
	}

	req := httptest.NewRequest(method, path, bytes.NewReader(payload))
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}

	resp := httptest.NewRecorder()
	handler.ServeHTTP(resp, req)
	return resp
}

func assertStatus(t *testing.T, resp *httptest.ResponseRecorder, want int) {
	t.Helper()
	if resp.Code != want {
		t.Fatalf("expected status %d, got %d: %s", want, resp.Code, resp.Body.String())
	}
}

func decodeResponse(t *testing.T, resp *httptest.ResponseRecorder, out any) {
	t.Helper()
	decodeStringResponse(t, resp.Body.String(), out)
}

func decodeStringResponse(t *testing.T, body string, out any) {
	t.Helper()
	if err := json.Unmarshal([]byte(body), out); err != nil {
		t.Fatalf("decode response: %v\nbody: %s", err, body)
	}
}

func readBody(t *testing.T, resp *httptest.ResponseRecorder) string {
	t.Helper()
	return resp.Body.String()
}

func findProvider(t *testing.T, providers []store.ProviderSetting, key string) store.ProviderSetting {
	t.Helper()
	for _, provider := range providers {
		if provider.Provider == key {
			return provider
		}
	}
	t.Fatalf("provider %q not found in response", key)
	return store.ProviderSetting{}
}
