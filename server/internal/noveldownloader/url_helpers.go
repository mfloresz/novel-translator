package noveldownloader

import (
	"fmt"
	"net/url"
	"path"
	"strings"
)

func extractBaseURL(pageURL string) string {
	u, err := url.Parse(pageURL)
	if err != nil {
		return pageURL
	}
	return fmt.Sprintf("%s://%s", u.Scheme, u.Host)
}

func resolveURL(base, href string) string {
	if strings.HasPrefix(href, "http://") || strings.HasPrefix(href, "https://") {
		return href
	}
	if strings.HasPrefix(href, "/") {
		return extractBaseURL(base) + href
	}
	baseURL := strings.TrimRight(base, "/")
	dir := path.Dir(baseURL)
	return dir + "/" + strings.TrimLeft(href, "/")
}
