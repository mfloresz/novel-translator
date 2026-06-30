package ai

type ProviderInfo struct {
	ID           string         `json:"id"`
	Name         string         `json:"name"`
	BaseURL      string         `json:"baseUrl"`
	Models       []string       `json:"models"`
	DefaultModel string         `json:"defaultModel"`
	OpenAICompat bool           `json:"openaiCompat"`
	GoAIOptions  map[string]any `json:"goaiOptions,omitempty"`
}

var knownProviders = []ProviderInfo{
	{
		ID:           "venice",
		Name:         "Venice",
		BaseURL:      "https://api.venice.ai/api/v1",
		Models:       []string{"deepseek-v4-flash", "mistral-small-3-2-24b-instruct", "google-gemma-4-31b-it"},
		DefaultModel: "deepseek-v4-flash",
		OpenAICompat: true,
		GoAIOptions: map[string]any{
			"useResponsesAPI":  false,
			"strictJsonSchema": true,
		},
	},

	{
		ID:           "opencode-go",
		Name:         "OpenCode Go",
		BaseURL:      "https://opencode.ai/zen/go/v1",
		Models:       []string{"mimo-v2.5", "deepseek-v4-flash"},
		DefaultModel: "mimo-v2.5",
		OpenAICompat: true,
		GoAIOptions: map[string]any{
			"useResponsesAPI":  false,
			"strictJsonSchema": true,
		},
	},
}

func Providers() []ProviderInfo {
	out := make([]ProviderInfo, len(knownProviders))
	copy(out, knownProviders)
	return out
}

func ProviderByID(id string) (ProviderInfo, bool) {
	for _, p := range knownProviders {
		if p.ID == id {
			return p, true
		}
	}
	return ProviderInfo{}, false
}

func DefaultProvider() ProviderInfo {
	if len(knownProviders) == 0 {
		return ProviderInfo{}
	}
	return knownProviders[0]
}
