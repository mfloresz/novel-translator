package api

import (
	"fmt"
	"strings"
)

func fillPrompt(template string, values map[string]string) string {
	result := template
	for key, value := range values {
		result = strings.ReplaceAll(result, key, value)
	}
	return strings.TrimSpace(result)
}

func formatGlossary(glossary []glossaryEntry) string {
	if len(glossary) == 0 {
		return "(sin glosario)"
	}
	lines := make([]string, 0, len(glossary))
	for _, entry := range glossary {
		lines = append(lines, fmt.Sprintf("- %s → %s", entry.Source, entry.Target))
	}
	return strings.Join(lines, "\n")
}
