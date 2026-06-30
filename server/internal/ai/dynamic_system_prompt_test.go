package ai

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestOpenAITranslateTitle_DynamicSystemPromptFlowsToProvider exercises the full
// real-world title flow: a dynamic system prompt (containing glossary entries,
// source and target languages substituted from the novel) must reach the wire
// intact, wrapped with the title-only JSON-schema hints, and placed in the
// right field for the configured provider (Responses `instructions` or Chat
// Completions `messages[role=system]`). Acts as a regression guard so that
// future changes to the title prompt pipeline do not silently drop dynamic
// content.
func TestOpenAITranslateTitle_DynamicSystemPromptFlowsToProvider(t *testing.T) {
	const dynamicBase = `You are a professional literary translator.

Source language: English
Target language: Spanish

Glossary:
- house → casa
- storm → tormenta
- child → niño/a

Preserve narrative voice. Do not add commentary.`

	wantSubstrings := []string{
		"professional literary translator",
		"Source language: English",
		"Target language: Spanish",
		"house → casa",
		"storm → tormenta",
		"child → niño/a",
		"JSON object with structured fields",
		"title_original",
		`{"title_translated": "..."}`,
		"structured output schema",
	}

	cases := []struct {
		name           string
		providerOpts   map[string]any
		wantPath       string
		extractSystem  func(body []byte) string
		wantFieldLabel string
	}{
		{
			name:           "responses_api_instructions",
			wantPath:       "/responses",
			wantFieldLabel: "instructions",
			extractSystem: func(body []byte) string {
				var req struct {
					Instructions string `json:"instructions"`
				}
				_ = json.Unmarshal(body, &req)
				return req.Instructions
			},
		},
		{
			name: "venice_chat_completions_system_role",
			providerOpts: map[string]any{
				"useResponsesAPI":  false,
				"strictJsonSchema": true,
			},
			wantPath:       "/chat/completions",
			wantFieldLabel: "messages[role=system].content",
			extractSystem: func(body []byte) string {
				var req struct {
					Messages []struct {
						Role    string `json:"role"`
						Content string `json:"content"`
					} `json:"messages"`
				}
				_ = json.Unmarshal(body, &req)
				for _, m := range req.Messages {
					if m.Role == "system" {
						return m.Content
					}
				}
				return ""
			},
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var capturedBody []byte
			var capturedPath string

			ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				capturedPath = r.URL.Path
				capturedBody, _ = io.ReadAll(r.Body)
				w.Header().Set("Content-Type", "application/json")
				if strings.HasSuffix(r.URL.Path, "/responses") {
					_, _ = w.Write([]byte(`{"id":"resp-x","model":"m","status":"completed","output":[{"type":"message","role":"assistant","content":[{"type":"output_text","text":"{\"title_translated\":\"T\"}"}]}],"usage":{"input_tokens":1,"output_tokens":1}}`))
				} else {
					_, _ = w.Write([]byte(`{"id":"chatcmpl-x","object":"chat.completion","model":"m","choices":[{"index":0,"message":{"role":"assistant","content":"{\"title_translated\":\"T\"}"},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}`))
				}
			}))
			defer ts.Close()

			provider := &OpenAIProvider{
				APIKey:          "test-key",
				BaseURL:         ts.URL,
				Model:           "test-model",
				ProviderOptions: tc.providerOpts,
			}

			_, err := provider.TranslateTitle(context.Background(), TranslateTitleInput{
				SystemPrompt:   dynamicBase,
				TitleOriginal:  "Chapter 1",
				SourceLanguage: "en",
				TargetLanguage: "es",
			})
			if err != nil {
				t.Fatalf("TranslateTitle returned error: %v", err)
			}

			if capturedPath != tc.wantPath {
				t.Fatalf("unexpected path: got %q, want %q", capturedPath, tc.wantPath)
			}

			got := tc.extractSystem(capturedBody)
			if got == "" {
				t.Fatalf("system prompt missing from %s in request body:\n%s", tc.wantFieldLabel, string(capturedBody))
			}

			for _, want := range wantSubstrings {
				if !strings.Contains(got, want) {
					t.Errorf("system prompt in %s is missing %q\n--- got ---\n%s", tc.wantFieldLabel, want, got)
				}
			}
		})
	}
}
