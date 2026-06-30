package epubimport

import (
	"archive/zip"
	"fmt"
	"io"
	"path"
)

func readZipFile(zr *zip.Reader, name string) ([]byte, error) {
	for _, f := range zr.File {
		if f.Name != name {
			continue
		}
		rc, err := f.Open()
		if err != nil {
			return nil, err
		}
		defer rc.Close()
		return io.ReadAll(rc)
	}
	return nil, fmt.Errorf("file not found: %s", name)
}

func resolveZipPath(opfPath, href string) string {
	base := path.Dir(opfPath)
	if base == "." || base == "" {
		return path.Clean(href)
	}
	return path.Clean(path.Join(base, href))
}
