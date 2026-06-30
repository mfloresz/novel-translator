package ai

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/zendev-sh/goai"
	"github.com/zendev-sh/goai/provider"
	"github.com/zendev-sh/goai/provider/openai"
)

type OpenAIProvider struct {
	APIKey  string
	BaseURL string
	Model   string
	Timeout time.Duration
	// ProviderOptions are passed to goai on every call. Use for provider-specific
	// behavior toggles like forcing Chat Completions (e.g. Venice) or strict JSON schema.
	ProviderOptions map[string]any
}

func (p *OpenAIProvider) model() (provider.LanguageModel, error) {
	if p == nil || p.APIKey == "" {
		return nil, fmt.Errorf("openai not configured")
	}
	opts := []openai.Option{openai.WithAPIKey(p.APIKey)}
	if p.BaseURL != "" {
		opts = append(opts, openai.WithBaseURL(p.BaseURL))
	}
	return openai.Chat(p.Model, opts...), nil
}

func (p *OpenAIProvider) opts() []goai.Option {
	var o []goai.Option
	if len(p.ProviderOptions) > 0 {
		opts := make(map[string]any, len(p.ProviderOptions))
		for k, v := range p.ProviderOptions {
			opts[k] = v
		}
		if strings.Contains(p.Model, "deepseek") {
			opts["structuredOutputs"] = false
		}
		o = append(o, goai.WithProviderOptions(opts))
	}
	return o
}

func (p *OpenAIProvider) textOpts() []goai.Option {
	var o []goai.Option
	if len(p.ProviderOptions) > 0 {
		opts := make(map[string]any, len(p.ProviderOptions))
		for k, v := range p.ProviderOptions {
			opts[k] = v
		}
		if strings.Contains(p.Model, "deepseek") {
			opts["structuredOutputs"] = false
		}
		delete(opts, "strictJsonSchema")
		o = append(o, goai.WithProviderOptions(opts))
	}
	return o
}

func (p *OpenAIProvider) TranslateTitle(ctx context.Context, in TranslateTitleInput) (string, error) {
	model, err := p.model()
	if err != nil {
		return "", err
	}
	opts := append(p.opts(),
		goai.WithSystem(buildTranslationTitleSystemPrompt(in)),
		goai.WithPrompt(buildTranslationTitlePrompt(in)),
		goai.WithTimeout(p.resolveTimeout()),
	)
	result, err := goai.GenerateObject[struct {
		TitleTranslated string `json:"title_translated"`
	}](ctx, model, opts...)
	if err != nil {
		return "", fmt.Errorf("openai translate title: %w", err)
	}
	return result.Object.TitleTranslated, nil
}

func (p *OpenAIProvider) TranslateText(ctx context.Context, in TranslateTextInput) (string, error) {
	model, err := p.model()
	if err != nil {
		return "", err
	}
	opts := append(p.textOpts(),
		goai.WithSystem(buildTranslationContentSystemPrompt(in)),
		goai.WithPrompt(buildTranslationContentPrompt(in)),
		goai.WithTimeout(p.resolveTimeout()),
	)
	result, err := goai.GenerateText(ctx, model, opts...)
	if err != nil {
		return "", fmt.Errorf("openai translate text: %w", err)
	}
	return strings.TrimSpace(result.Text), nil
}

func (p *OpenAIProvider) Refine(ctx context.Context, in RefineInput) (RefineOutput, error) {
	model, err := p.model()
	if err != nil {
		return RefineOutput{}, err
	}
	opts := append(p.opts(),
		goai.WithPrompt(in.TranslatedText),
		goai.WithTimeout(p.resolveTimeout()),
	)
	result, err := goai.GenerateObject[RefineOutput](ctx, model, opts...)
	if err != nil {
		return RefineOutput{}, fmt.Errorf("openai refine: %w", err)
	}
	return result.Object, nil
}

func (p *OpenAIProvider) Check(ctx context.Context, in CheckInput) (CheckOutput, error) {
	model, err := p.model()
	if err != nil {
		return CheckOutput{}, err
	}
	user := fmt.Sprintf("Original: %s\nTranslated: %s", in.ContentOriginal, in.ContentTranslated)
	system := "Analyze the following text for translation quality."
	if trimmed := strings.TrimSpace(in.SystemPrompt); trimmed != "" {
		system = trimmed
	}
	opts := append(p.opts(),
		goai.WithSystem(system),
		goai.WithPrompt(user),
		goai.WithTimeout(p.resolveTimeout()),
	)
	result, err := goai.GenerateObject[CheckOutput](ctx, model, opts...)
	if err != nil {
		return CheckOutput{}, fmt.Errorf("openai check: %w", err)
	}
	return result.Object, nil
}

func (p *OpenAIProvider) resolveTimeout() time.Duration {
	if p.Timeout > 0 {
		return p.Timeout
	}
	return 60 * time.Second
}
