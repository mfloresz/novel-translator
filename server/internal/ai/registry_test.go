package ai

import "testing"

func TestProvidersContainKnownEntries(t *testing.T) {
	ids := map[string]bool{}
	for _, p := range Providers() {
		if p.ID == "" {
			t.Fatalf("provider with empty id: %+v", p)
		}
		if p.BaseURL == "" {
			t.Fatalf("provider %q has empty base url", p.ID)
		}
		if len(p.Models) == 0 {
			t.Fatalf("provider %q has no models", p.ID)
		}
		if p.DefaultModel == "" {
			t.Fatalf("provider %q has empty default model", p.ID)
		}
		found := false
		for _, m := range p.Models {
			if m == p.DefaultModel {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("provider %q default model %q not in models list %v", p.ID, p.DefaultModel, p.Models)
		}
		if ids[p.ID] {
			t.Fatalf("duplicate provider id %q", p.ID)
		}
		ids[p.ID] = true
	}
	for _, want := range []string{"venice", "opencode-go"} {
		if !ids[want] {
			t.Fatalf("missing known provider %q", want)
		}
	}
}

func TestProviderByIDOpenCodeGo(t *testing.T) {
	info, ok := ProviderByID("opencode-go")
	if !ok {
		t.Fatal("opencode-go provider not registered")
	}
	if info.BaseURL != "https://opencode.ai/zen/go/v1" {
		t.Fatalf("unexpected base url: %q", info.BaseURL)
	}
	if !info.OpenAICompat {
		t.Fatal("opencode-go should be OpenAI compatible")
	}
	if got, _ := info.GoAIOptions["useResponsesAPI"].(bool); got {
		t.Fatal("opencode-go should force chat/completions instead of responses API")
	}
	if got, _ := info.GoAIOptions["strictJsonSchema"].(bool); !got {
		t.Fatal("opencode-go should enable strict JSON schema")
	}
	wantModels := map[string]bool{"mimo-v2.5": true, "deepseek-v4-flash": true}
	if len(info.Models) != len(wantModels) {
		t.Fatalf("unexpected model list: %v", info.Models)
	}
	for _, m := range info.Models {
		if !wantModels[m] {
			t.Fatalf("unexpected model %q in opencode-go", m)
		}
	}
}

func TestProviderByIDUnknown(t *testing.T) {
	if _, ok := ProviderByID("does-not-exist"); ok {
		t.Fatal("unknown provider should not be found")
	}
}
