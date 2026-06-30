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

type capturedResponsesRequest struct {
	Model        string         `json:"model"`
	Instructions string         `json:"instructions"`
	Input        []inputItem    `json:"input"`
	Text         map[string]any `json:"text"`
}

type inputItem struct {
	Role    string         `json:"role"`
	Content []contentBlock `json:"content"`
}

type contentBlock struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

func extractUserText(req capturedResponsesRequest) string {
	for _, item := range req.Input {
		if item.Role != "user" {
			continue
		}
		for _, block := range item.Content {
			if block.Type == "input_text" {
				return block.Text
			}
		}
	}
	return ""
}

func TestOpenAITranslateTitle_SendsStructuredTitlePayloadAndParsesSchemaResponse(t *testing.T) {
	var captured capturedResponsesRequest

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Fatalf("unexpected method: %s", r.Method)
		}
		if r.URL.Path != "/responses" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer test-key" {
			t.Fatalf("unexpected auth header: %q", got)
		}
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed reading request body: %v", err)
		}
		if err := json.Unmarshal(body, &captured); err != nil {
			t.Fatalf("failed decoding request body: %v\nbody: %s", err, string(body))
		}

		responseContent, err := json.Marshal(map[string]string{
			"title_translated": "Capítulo Siete",
		})
		if err != nil {
			t.Fatalf("failed encoding provider response content: %v", err)
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id":     "resp-test",
			"model":  "test-model",
			"status": "completed",
			"output": []map[string]any{{
				"type": "message",
				"role": "assistant",
				"content": []map[string]any{{
					"type": "output_text",
					"text": string(responseContent),
				}},
			}},
			"usage": map[string]int{"input_tokens": 10, "output_tokens": 20},
		})
	}))
	defer ts.Close()

	provider := &OpenAIProvider{
		APIKey:  "test-key",
		BaseURL: ts.URL,
		Model:   "test-model",
	}

	translatedTitle, err := provider.TranslateTitle(context.Background(), TranslateTitleInput{
		SystemPrompt:   "Translate from English to Spanish.\n\nGlossary:\nhouse → casa",
		TitleOriginal:  "Chapter Seven",
		SourceLanguage: "en",
		TargetLanguage: "es",
	})
	if err != nil {
		t.Fatalf("TranslateTitle returned error: %v", err)
	}

	if translatedTitle != "Capítulo Siete" {
		t.Fatalf("unexpected translated title\nwant: %q\ngot:  %q", "Capítulo Siete", translatedTitle)
	}

	if captured.Model != "test-model" {
		t.Fatalf("unexpected model: %q", captured.Model)
	}
	if strings.TrimSpace(captured.Instructions) == "" {
		t.Fatal("instructions (system prompt) should not be empty")
	}

	userText := extractUserText(captured)
	if userText == "" {
		t.Fatal("user message content should not be empty")
	}

	var userPayload map[string]any
	if err := json.Unmarshal([]byte(userText), &userPayload); err != nil {
		t.Fatalf("user message is not valid JSON: %v\ncontent: %s", err, userText)
	}
	if len(userPayload) != 1 {
		t.Fatalf("user payload should have exactly 1 field, got %d: %#v", len(userPayload), userPayload)
	}
	if got := userPayload["title_original"]; got != "Chapter Seven" {
		t.Fatalf("unexpected title_original\nwant: %q\ngot:  %#v", "Chapter Seven", got)
	}
	for _, forbidden := range []string{
		"text_original",
		"source_language", "target_language",
		"previous_title_original", "previous_title_translated",
	} {
		if _, ok := userPayload[forbidden]; ok {
			t.Fatalf("user payload must not include %q", forbidden)
		}
	}

	textFormat, ok := captured.Text["format"].(map[string]any)
	if !ok {
		t.Fatalf("text.format must be set, got: %#v", captured.Text)
	}
	if textFormat["type"] != "json_schema" {
		t.Fatalf("text.format.type = %v, want json_schema", textFormat["type"])
	}
}

func TestOpenAITranslateTitle_IncludesPreviousTitleInUserPayload(t *testing.T) {
	var captured capturedResponsesRequest

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		if err := json.Unmarshal(body, &captured); err != nil {
			t.Fatalf("failed decoding request body: %v\nbody: %s", err, string(body))
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id":     "resp-test",
			"model":  "test-model",
			"status": "completed",
			"output": []map[string]any{{
				"type": "message",
				"role": "assistant",
				"content": []map[string]any{{
					"type": "output_text",
					"text": `{"title_translated":"Capítulo Siete"}`,
				}},
			}},
		})
	}))
	defer ts.Close()

	provider := &OpenAIProvider{
		APIKey:  "test-key",
		BaseURL: ts.URL,
		Model:   "test-model",
	}

	if _, err := provider.TranslateTitle(context.Background(), TranslateTitleInput{
		SystemPrompt:       "Traduce fielmente.",
		TitleOriginal:      "Chapter Seven",
		PreviousTitleOrig:  "Chapter Six",
		PreviousTitleTrans: "Capítulo Seis",
		SourceLanguage:     "en",
		TargetLanguage:     "es",
	}); err != nil {
		t.Fatalf("TranslateTitle returned error: %v", err)
	}

	userText := extractUserText(captured)
	var userPayload map[string]any
	if err := json.Unmarshal([]byte(userText), &userPayload); err != nil {
		t.Fatalf("user message is not valid JSON: %v\ncontent: %s", err, userText)
	}

	if got := userPayload["title_original"]; got != "Chapter Seven" {
		t.Fatalf("unexpected title_original: %#v", got)
	}
	if got, ok := userPayload["previous_title_original"]; !ok || got != "Chapter Six" {
		t.Fatalf("previous_title_original missing or wrong: %#v (ok=%v)", got, ok)
	}
	if got, ok := userPayload["previous_title_translated"]; !ok || got != "Capítulo Seis" {
		t.Fatalf("previous_title_translated missing or wrong: %#v (ok=%v)", got, ok)
	}
}

func TestOpenAITranslateText_SendsPlainTextPromptWithoutSchema(t *testing.T) {
	var captured capturedResponsesRequest

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		if err != nil {
			t.Fatalf("failed reading request body: %v", err)
		}
		if err := json.Unmarshal(body, &captured); err != nil {
			t.Fatalf("failed decoding request body: %v\nbody: %s", err, string(body))
		}
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id":     "resp-test",
			"model":  "test-model",
			"status": "completed",
			"output": []map[string]any{{
				"type": "message",
				"role": "assistant",
				"content": []map[string]any{{
					"type": "output_text",
					"text": "Texto del cuerpo traducido",
				}},
			}},
		})
	}))
	defer ts.Close()

	provider := &OpenAIProvider{
		APIKey:  "test-key",
		BaseURL: ts.URL,
		Model:   "test-model",
	}

	translatedText, err := provider.TranslateText(context.Background(), TranslateTextInput{
		SystemPrompt:    "Translate faithfully.",
		TextToTranslate: "Body text",
		SourceLanguage:  "en",
		TargetLanguage:  "es",
	})
	if err != nil {
		t.Fatalf("TranslateText returned error: %v", err)
	}

	if translatedText != "Texto del cuerpo traducido" {
		t.Fatalf("unexpected translated text\nwant: %q\ngot:  %q", "Texto del cuerpo traducido", translatedText)
	}

	userText := extractUserText(captured)
	if userText != "Body text" {
		t.Fatalf("plain-text user prompt mismatch\nwant: %q\ngot:  %q", "Body text", userText)
	}
	if strings.Contains(captured.Instructions, "structured output schema") {
		t.Fatalf("content instructions must not require structured output:\n%s", captured.Instructions)
	}
	if format, ok := captured.Text["format"]; ok {
		t.Fatalf("plain-text translation must not request text.format schema, got: %#v", format)
	}
}
