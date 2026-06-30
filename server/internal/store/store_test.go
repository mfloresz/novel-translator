package store

import (
	"path/filepath"
	"strings"
	"testing"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
	"translator-server/internal/secure"
)

func TestClampTextTruncatesAndStrips(t *testing.T) {
	got := clampText("  hello world  ", 5)
	if got != "hello" {
		t.Fatalf("expected %q, got %q", "hello", got)
	}
	if clampText("short", 100) != "short" {
		t.Fatalf("short string should be preserved")
	}
	if clampText(strings.Repeat("a", 5000), 5000) != strings.Repeat("a", 5000) {
		t.Fatalf("string at boundary should be preserved")
	}
}

func TestEnsureSchemaMigratesUsersCollectionWithActiveProvider(t *testing.T) {
	dataDir := t.TempDir()
	app := pocketbase.NewWithConfig(pocketbase.Config{DefaultDataDir: dataDir})
	if err := app.Bootstrap(); err != nil {
		t.Fatalf("bootstrap pocketbase: %v", err)
	}

	legacyUsers, err := app.FindCollectionByNameOrId(UsersCollection)
	if err != nil {
		t.Fatalf("find bootstrap users collection: %v", err)
	}
	legacyUsers.Fields.RemoveByName("theme")
	legacyUsers.Fields.RemoveByName("active_provider")
	if legacyUsers.Fields.GetByName("name") == nil {
		legacyUsers.Fields.Add(&core.TextField{Name: "name", Max: 120})
	}
	if err := app.Save(legacyUsers); err != nil {
		t.Fatalf("save legacy users collection: %v", err)
	}

	encryptor, err := secure.NewEncryptorFromConfig("", filepath.Join(dataDir, "app.key"))
	if err != nil {
		t.Fatalf("create encryptor: %v", err)
	}

	st := New(app, encryptor)
	if err := st.EnsureSchema(); err != nil {
		t.Fatalf("ensure schema: %v", err)
	}

	users, err := app.FindCollectionByNameOrId(UsersCollection)
	if err != nil {
		t.Fatalf("find users collection: %v", err)
	}
	if users.Fields.GetByName("active_provider") == nil {
		t.Fatal("expected active_provider field to be added to existing users collection")
	}
	if users.Fields.GetByName("theme") == nil {
		t.Fatal("expected theme field to be added to existing users collection")
	}
}

func TestRunDatabaseMigrationsBackfillsAndRemovesLegacyNovelFields(t *testing.T) {
	dataDir := t.TempDir()
	app := pocketbase.NewWithConfig(pocketbase.Config{DefaultDataDir: dataDir})
	if err := app.Bootstrap(); err != nil {
		t.Fatalf("bootstrap pocketbase: %v", err)
	}

	encryptor, err := secure.NewEncryptorFromConfig("", filepath.Join(dataDir, "app.key"))
	if err != nil {
		t.Fatalf("create encryptor: %v", err)
	}

	st := New(app, encryptor)
	if err := st.EnsureSchema(); err != nil {
		t.Fatalf("ensure schema: %v", err)
	}

	novels, err := app.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		t.Fatalf("find novels collection: %v", err)
	}
	if sourceTitleField, ok := novels.Fields.GetByName("source_title").(*core.TextField); ok {
		sourceTitleField.Required = false
		novels.Fields.Add(sourceTitleField)
	} else {
		t.Fatal("expected source_title text field")
	}
	for _, field := range []core.Field{
		&core.TextField{Name: "title", Max: 250},
		&core.TextField{Name: "author", Max: 250},
		&core.EditorField{Name: "description"},
		&core.TextField{Name: "prompts"},
		&core.TextField{Name: "source_metadata"},
		&core.TextField{Name: "target_metadata"},
	} {
		if novels.Fields.GetByName(field.GetName()) == nil {
			novels.Fields.Add(field)
		}
	}
	if err := app.Save(novels); err != nil {
		t.Fatalf("save novels collection with legacy fields: %v", err)
	}

	users, err := app.FindCollectionByNameOrId(UsersCollection)
	if err != nil {
		t.Fatalf("find users collection: %v", err)
	}
	owner := core.NewRecord(users)
	owner.Set("email", "owner@example.com")
	owner.Set("password", "secret123")
	owner.Set("passwordConfirm", "secret123")
	if err := app.Save(owner); err != nil {
		t.Fatalf("save owner user: %v", err)
	}

	record := core.NewRecord(novels)
	record.Set("owner", owner.Id)
	record.Set("source_language", "en")
	record.Set("target_language", "es")
	record.Set("source_title", "")
	record.Set("source_author", "")
	record.Set("source_description", "")
	record.Set("title", "Legacy Title")
	record.Set("author", "Legacy Author")
	record.Set("description", "Legacy Description")
	record.Set("prompts", `{"translation":{"systemPrompt":"legacy translation system","userPrompt":"legacy translation user"},"check":{"systemPrompt":"legacy check system"}}`)
	if err := app.Save(record); err != nil {
		t.Fatalf("save legacy novel record: %v", err)
	}

	needsMigration, err := st.NeedsDatabaseMigration()
	if err != nil {
		t.Fatalf("detect database migrations: %v", err)
	}
	if !needsMigration {
		t.Fatal("expected legacy novel schema/data to require migration")
	}

	if err := st.RunDatabaseMigrations(); err != nil {
		t.Fatalf("run database migrations: %v", err)
	}

	migrated, err := app.FindRecordById(NovelsCollection, record.Id)
	if err != nil {
		t.Fatalf("find migrated novel: %v", err)
	}
	if got := migrated.GetString("source_title"); got != "Legacy Title" {
		t.Fatalf("source_title = %q, want %q", got, "Legacy Title")
	}
	if got := migrated.GetString("source_author"); got != "Legacy Author" {
		t.Fatalf("source_author = %q, want %q", got, "Legacy Author")
	}
	if got := migrated.GetString("source_description"); got != "Legacy Description" {
		t.Fatalf("source_description = %q, want %q", got, "Legacy Description")
	}
	if got := migrated.GetString("translation_system_prompt"); got != "legacy translation system" {
		t.Fatalf("translation_system_prompt = %q", got)
	}
	if got := migrated.GetString("translation_user_prompt"); got != "legacy translation user" {
		t.Fatalf("translation_user_prompt = %q", got)
	}
	if got := migrated.GetString("check_system_prompt"); got != "legacy check system" {
		t.Fatalf("check_system_prompt = %q", got)
	}

	novels, err = app.FindCollectionByNameOrId(NovelsCollection)
	if err != nil {
		t.Fatalf("reload novels collection: %v", err)
	}
	for _, fieldName := range []string{"title", "author", "description", "prompts", "source_metadata", "target_metadata"} {
		if novels.Fields.GetByName(fieldName) != nil {
			t.Fatalf("expected legacy field %q to be removed", fieldName)
		}
	}

	needsMigration, err = st.NeedsDatabaseMigration()
	if err != nil {
		t.Fatalf("detect database migrations after migration: %v", err)
	}
	if needsMigration {
		t.Fatal("did not expect remaining legacy migration work after migration run")
	}
}
