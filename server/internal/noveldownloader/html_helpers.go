package noveldownloader

import "strings"

func CleanTitle(title string) string {
	title = strings.TrimSpace(title)
	title = strings.Join(strings.Fields(title), " ")
	return title
}
