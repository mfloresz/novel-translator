import JSZip from "jszip";

export type EpubChapter = {
  id: string;
  title: string;
  content: string;
  order: number;
};

export type EpubMetadata = {
  title: string;
  author?: string;
  description?: string;
  language: string;
  identifier?: string;
  publisher?: string;
  coverDataUrl?: string;
};

export type EpubBuildOptions = {
  metadata: EpubMetadata;
  chapters: EpubChapter[];
  cssExtra?: string;
};

function escapeXml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function slugify(text: string, fallback: string): string {
  const cleaned = (text || fallback)
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

function contentToHtml(markdown: string): string {
  let text = (markdown || "").replace(/\r\n/g, "\n");
  text = text.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.*)$/gm, "<h1>$1</h1>");
  text = text.replace(/\*\*\*([^*\n]+)\*\*\*/g, "<strong><em>$1</em></strong>");
  text = text.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>");
  text = text.replace(/_([^_\n]+)_/g, "<em>$1</em>");
  text = text.replace(/^>\s?(.*)$/gm, "<blockquote>$1</blockquote>");
  text = text.replace(/^---\s*$/gm, "<hr/>");
  text = text.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");

  const blocks = text.split(/\n{2,}/);
  const out: string[] = [];
  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    if (/^<(h\d|ul|ol|li|blockquote|hr|p|pre|img)/.test(trimmed)) {
      out.push(trimmed);
    } else {
      const withBreaks = trimmed
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .join("<br/>");
      out.push(`<p>${withBreaks}</p>`);
    }
  }
  return out.join("\n");
}

function buildChapterXhtml(chapter: EpubChapter): string {
  const title = escapeXml(chapter.title || `Capítulo ${chapter.order}`);
  const body = contentToHtml(chapter.content);
  return `<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" lang="es">\n<head>\n  <meta charset="utf-8"/>\n  <title>${title}</title>\n  <link rel="stylesheet" type="text/css" href="../styles/main.css"/>\n</head>\n<body>\n  <section epub:type="chapter" id="chapter-${chapter.order}">\n    <h1>${title}</h1>\n    ${body}\n  </section>\n</body>\n</html>`;
}

const DEFAULT_CSS = `body {\n  font-family: Georgia, "Times New Roman", serif;\n  line-height: 1.6;\n  margin: 1em;\n}\nh1, h2, h3 { font-family: Georgia, serif; page-break-after: avoid; }\nh1 { font-size: 1.6em; margin: 1.2em 0 0.6em; }\nh2 { font-size: 1.3em; margin: 1em 0 0.5em; }\nh3 { font-size: 1.1em; margin: 0.8em 0 0.4em; }\np { margin: 0 0 1em; text-indent: 0; }\nblockquote { margin: 1em 2em; font-style: italic; }\nhr { border: 0; border-top: 1px solid #ccc; margin: 1.5em 0; }\nli { margin: 0.3em 0; }\n.cover { text-align: center; margin: 0; padding: 0; }\n.cover img { max-width: 100%; height: auto; }\n.title-page { text-align: center; margin-top: 4em; }\n.title-page h1 { font-size: 2em; }\n.title-page p { font-style: italic; }\n`;

function dataUrlToBytes(dataUrl: string): { bytes: Uint8Array; mime: string } {
  const match = dataUrl.match(/^data:([^;]+);base64,(.*)$/);
  if (!match) throw new Error("Cover image must be a base64 data URL");
  const mime = match[1];
  const binary = atob(match[2]);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return { bytes, mime };
}

function mimeToExt(mime: string): string {
  if (mime.includes("jpeg") || mime.includes("jpg")) return "jpg";
  if (mime.includes("png")) return "png";
  if (mime.includes("webp")) return "webp";
  if (mime.includes("gif")) return "gif";
  return "img";
}

function buildContainerXml(): string {
  return `<?xml version="1.0"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n  </rootfiles>\n</container>`;
}

function buildContentOpf(meta: EpubMetadata, chapters: EpubChapter[], hasCover: boolean, coverId: string | null): string {
  const id = meta.identifier || `urn:uuid:${crypto.randomUUID()}`;
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const manifestItems = [
    `<item id="title-page" href="text/title.xhtml" media-type="application/xhtml+xml"/>`,
    ...chapters.map(
      (chapter) => `<item id="${slugify(chapter.title, `chapter-${chapter.order}`)}" href="text/${slugify(chapter.title, `chapter-${chapter.order}`)}.xhtml" media-type="application/xhtml+xml"/>`,
    ),
    `<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>`,
    `<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>`,
    `<item id="css" href="styles/main.css" media-type="text/css"/>`,
  ];

  if (hasCover && coverId) {
    const mime = meta.coverDataUrl?.split(";")[0].replace("data:", "") || "image/jpeg";
    manifestItems.push(
      `<item id="${coverId}" href="images/cover.${mimeToExt(mime)}" media-type="${mime}" properties="cover-image"/>`,
    );
  }

  const spineItems = [
    `<itemref idref="title-page"/>`,
    ...chapters.map((chapter) => `<itemref idref="${slugify(chapter.title, `chapter-${chapter.order}`)}"/>`),
  ].join("\n    ");

  return `<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="${meta.language || "es"}">\n  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n    <dc:identifier id="bookid">${escapeXml(id)}</dc:identifier>\n    <dc:title>${escapeXml(meta.title)}</dc:title>\n    <dc:creator>${escapeXml(meta.author || "Desconocido")}</dc:creator>\n    <dc:language>${escapeXml(meta.language || "es")}</dc:language>\n    ${meta.publisher ? `<dc:publisher>${escapeXml(meta.publisher)}</dc:publisher>` : ""}\n    ${meta.description ? `<dc:description>${escapeXml(meta.description)}</dc:description>` : ""}\n    <meta property="dcterms:modified">${now}</meta>\n    ${hasCover ? `<meta name="cover" content="${coverId || "cover-img"}"/>` : ""}\n  </metadata>\n  <manifest>\n    ${manifestItems.join("\n    ")}\n  </manifest>\n  <spine toc="ncx">\n    ${spineItems}\n  </spine>\n</package>`;
}

function buildNav(chapters: EpubChapter[]): string {
  const items = chapters.map((chapter) => `<li><a href="text/${slugify(chapter.title, `chapter-${chapter.order}`)}.xhtml">${escapeXml(chapter.title)}</a></li>`).join("\n      ");
  return `<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="es">\n<head>\n  <meta charset="utf-8"/>\n  <title>Tabla de contenidos</title>\n  <link rel="stylesheet" type="text/css" href="styles/main.css"/>\n</head>\n<body>\n  <nav epub:type="toc" id="toc">\n    <h1>Tabla de contenidos</h1>\n    <ol>\n      ${items}\n    </ol>\n  </nav>\n</body>\n</html>`;
}

function buildNcx(meta: EpubMetadata, chapters: EpubChapter[]): string {
  const id = meta.identifier || `urn:uuid:${crypto.randomUUID()}`;
  const navPoints = chapters.map((chapter, index) => {
    const order = index + 1;
    return `<navPoint id="navpoint-${order}" playOrder="${order}">\n        <navLabel><text>${escapeXml(chapter.title)}</text></navLabel>\n        <content src="text/${slugify(chapter.title, `chapter-${chapter.order}`)}.xhtml"/>\n      </navPoint>`;
  }).join("\n      ");
  return `<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n  <head>\n    <meta name="dtb:uid" content="${escapeXml(id)}"/>\n    <meta name="dtb:depth" content="2"/>\n    <meta name="dtb:totalPageCount" content="0"/>\n    <meta name="dtb:maxPageNumber" content="0"/>\n  </head>\n  <docTitle><text>${escapeXml(meta.title)}</text></docTitle>\n  <navMap>\n      ${navPoints}\n  </navMap>\n</ncx>`;
}

function buildTitlePage(meta: EpubMetadata, hasCover: boolean, coverHref: string | null): string {
  const cover = hasCover && coverHref ? `<div class="cover"><img src="${coverHref}" alt="Portada"/></div>` : "";
  return `<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" lang="es">\n<head>\n  <meta charset="utf-8"/>\n  <title>${escapeXml(meta.title)}</title>\n  <link rel="stylesheet" type="text/css" href="styles/main.css"/>\n</head>\n<body>\n  ${cover}\n  <section class="title-page">\n    <h1>${escapeXml(meta.title)}</h1>\n    ${meta.author ? `<p>${escapeXml(meta.author)}</p>` : ""}\n  </section>\n</body>\n</html>`;
}

export async function buildEpub(options: EpubBuildOptions): Promise<Blob> {
  const zip = new JSZip();
  const meta = options.metadata;
  const orderedChapters = [...options.chapters].sort((a, b) => a.order - b.order);

  zip.file("mimetype", "application/epub+zip", { compression: "STORE" });
  zip.file("META-INF/container.xml", buildContainerXml());
  zip.file("META-INF/com.apple.ibooks.display-options.xml", `<?xml version="1.0" encoding="UTF-8"?>\n<display_options>\n  <platform name="*">\n    <option name="specified-fonts">true</option>\n  </platform>\n</display_options>`);

  const oebps = zip.folder("OEBPS")!;
  oebps.file("styles/main.css", (options.cssExtra ? `${options.cssExtra}\n` : "") + DEFAULT_CSS);
  oebps.file(
    "text/title.xhtml",
    buildTitlePage(meta, Boolean(meta.coverDataUrl), meta.coverDataUrl ? `../images/cover.${mimeToExt(meta.coverDataUrl.split(";")[0].replace("data:", ""))}` : null),
  );

  const textFolder = oebps.folder("text")!;
  for (const chapter of orderedChapters) {
    textFolder.file(`${slugify(chapter.title, `chapter-${chapter.order}`)}.xhtml`, buildChapterXhtml(chapter));
  }

  oebps.file("nav.xhtml", buildNav(orderedChapters));
  oebps.file("toc.ncx", buildNcx(meta, orderedChapters));

  let coverId: string | null = null;
  if (meta.coverDataUrl) {
    const { bytes, mime } = dataUrlToBytes(meta.coverDataUrl);
    coverId = "cover-img";
    oebps.folder("images")?.file(`cover.${mimeToExt(mime)}`, bytes);
  }

  oebps.file("content.opf", buildContentOpf(meta, orderedChapters, Boolean(meta.coverDataUrl), coverId));

  return zip.generateAsync({ type: "blob", mimeType: "application/epub+zip" });
}

export function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
