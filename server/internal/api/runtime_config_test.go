package api

import (
	"testing"

	"translator-server/internal/ai"
	"translator-server/internal/store"
)

func TestResolveJobConfigAppliesNovelAutoSegmentOverride(t *testing.T) {
	env := newAPITestEnv(t)
	alice := registerUser(t, env.handler, "alice-autosegment@example.com", "secret123", "Alice")
	novel := createNovel(t, env.handler, alice.Token, "Trabajo", "es", "en")

	if _, err := env.store.SaveAppSettings(alice.User.ID, store.AppSettings{
		AI: store.AISettings{
			Provider:  "venice",
			BaseURL:   "https://api.venice.ai/api/v1",
			Model:     "deepseek-v4-flash",
			TimeoutMs: 600000,
		},
		Translation: store.DefaultTranslationDefaults,
	}); err != nil {
		t.Fatalf("save app settings: %v", err)
	}

	if _, err := env.store.UpdateNovel(alice.User.ID, novel.ID, map[string]any{
		"translationOptions": map[string]any{
			"autoSegment": false,
		},
	}); err != nil {
		t.Fatalf("update novel translation options: %v", err)
	}

	storedNovel, err := env.store.GetOwnedNovel(alice.User.ID, novel.ID)
	if err != nil {
		t.Fatalf("get owned novel: %v", err)
	}

	cfg, err := New(env.store, nil).resolveJobConfig(storedNovel, &store.Job{
		OwnerID: alice.User.ID,
		NovelID: novel.ID,
	})
	if err != nil {
		t.Fatalf("resolve job config: %v", err)
	}

	if cfg.Translation.AutoSegment {
		t.Fatalf("expected novel translationOptions.autoSegment=false to override global autoSegment=true")
	}
}

func TestNewAIProviderKnownProviderUsesResolvedBaseURLAndProviderOptions(t *testing.T) {
	env := newAPITestEnv(t)
	server := New(env.store, nil)

	provider, err := server.newAIProvider(store.AISettings{
		Provider:  "opencode-go",
		APIKey:    "test-key",
		BaseURL:   "https://custom.opencode.example/v1",
		Model:     "deepseek-v4-flash",
		TimeoutMs: 45000,
	})
	if err != nil {
		t.Fatalf("new AI provider: %v", err)
	}

	op, ok := provider.(*ai.OpenAIProvider)
	if !ok {
		t.Fatalf("expected *ai.OpenAIProvider, got %T", provider)
	}
	if op.BaseURL != "https://custom.opencode.example/v1" {
		t.Fatalf("expected resolved base URL to be preserved, got %q", op.BaseURL)
	}
	if got, _ := op.ProviderOptions["useResponsesAPI"].(bool); got {
		t.Fatal("expected opencode-go provider to disable responses API")
	}
	if got, _ := op.ProviderOptions["strictJsonSchema"].(bool); !got {
		t.Fatal("expected opencode-go provider to enable strict JSON schema")
	}
}

func TestJobRecordIncludesAutoSegmentEnabled(t *testing.T) {
	payload := jobRecord(store.Job{
		ID:                        "job-1",
		NovelID:                   "novel-1",
		Status:                    "running",
		AutoSegmentEnabled:        true,
		AutoSegmentCurrentIndex:   2,
		AutoSegmentCompletedCount: 1,
	})

	value, ok := payload["autoSegmentEnabled"].(bool)
	if !ok {
		t.Fatalf("expected autoSegmentEnabled bool in job payload, got %T", payload["autoSegmentEnabled"])
	}
	if !value {
		t.Fatalf("expected autoSegmentEnabled=true in job payload")
	}
	currentIndex, ok := payload["autoSegmentCurrentIndex"].(int)
	if !ok {
		t.Fatalf("expected autoSegmentCurrentIndex int in job payload, got %T", payload["autoSegmentCurrentIndex"])
	}
	if currentIndex != 2 {
		t.Fatalf("expected autoSegmentCurrentIndex=2, got %d", currentIndex)
	}
	completedCount, ok := payload["autoSegmentCompletedCount"].(int)
	if !ok {
		t.Fatalf("expected autoSegmentCompletedCount int in job payload, got %T", payload["autoSegmentCompletedCount"])
	}
	if completedCount != 1 {
		t.Fatalf("expected autoSegmentCompletedCount=1, got %d", completedCount)
	}
}
