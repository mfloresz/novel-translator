import JSZip from "jszip";

export type ImportedChapter = {
  id: string;
  title: string;
  content: string;
  order: number;
};

export type ImportedBook = {
  title: string;
  author: string;
  description: string;
  language: string;
  chapters: ImportedChapter[];
};

const HTML_ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
  ndash: "–",
  mdash: "—",
  hellip: "…",
  laquo: "«",
  raquo: "»",
};

function decodeEntities(input: string): string {
  return input.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, body: string) => {
    if (body.startsWith("#x") || body.startsWith("#X")) {
      return String.fromCodePoint(parseInt(body.slice(2), 16));
    }
    if (body.startsWith("#")) {
      return String.fromCodePoint(parseInt(body.slice(1), 10));
    }
    return HTML_ENTITIES[body.toLowerCase()] ?? match;
  });
}

function htmlToMarkdown(html: string): string {
  let text = html;
  text = text.replace(/<br\s*\/?>/gi, "\n");
  text = text.replace(/<\/p>/gi, "\n\n");
  text = text.replace(/<p[^>]*>/gi, "");
  text = text.replace(/<h1[^>]*>(.*?)<\/h1>/gi, "# $1\n\n");
  text = text.replace(/<h2[^>]*>(.*?)<\/h2>/gi, "## $1\n\n");
  text = text.replace(/<h3[^>]*>(.*?)<\/h3>/gi, "### $1\n\n");
  text = text.replace(/<h4[^>]*>(.*?)<\/h4>/gi, "#### $1\n\n");
  text = text.replace(/<hr\s*\/?>/gi, "\n---\n\n");
  text = text.replace(/<strong[^>]*>(.*?)<\/strong>/gi, "**$1**");
  text = text.replace(/<b[^>]*>(.*?)<\/b>/gi, "**$1**");
  text = text.replace(/<em[^>]*>(.*?)<\/em>/gi, "*$1*");
  text = text.replace(/<i[^>]*>(.*?)<\/i>/gi, "*$1*");
  text = text.replace(/<blockquote[^>]*>(.*?)<\/blockquote>/gis, (_, inner: string) => {
    return inner
      .split("\n")
      .map((line) => `> ${line.trim()}`)
      .join("\n") + "\n\n";
  });
  text = text.replace(/<li[^>]*>(.*?)<\/li>/gi, "- $1\n");
  text = text.replace(/<\/(ul|ol)>/gi, "\n");
  text = text.replace(/<(ul|ol)[^>]*>/gi, "");
  text = text.replace(/<[^>]+>/g, "");
  text = decodeEntities(text);
  text = text.replace(/[ \t]+\n/g, "\n");
  text = text.replace(/\n{3,}/g, "\n\n");
  return text.trim();
}

async function parseContainer(zip: JSZip): Promise<{ opfPath: string }> {
  const xml = await zip.file("META-INF/container.xml")?.async("string");
  const match = xml?.match(/<rootfile[^>]*full-path="([^"]+)"/);
  if (!match) throw new Error("Invalid EPUB: container.xml missing rootfile");
  return { opfPath: match[1] };
}

type SpineEntry = { id: string; href: string; mediaType: string };

async function readOpf(zip: JSZip, opfPath: string): Promise<{
  metadata: Record<string, string[]>;
  manifest: SpineEntry[];
  spine: string[];
  opfDir: string;
}> {
  const xml = await zip.file(opfPath)?.async("string");
  if (!xml) throw new Error("Invalid EPUB: OPF not found");

  const opfDir = opfPath.includes("/") ? opfPath.slice(0, opfPath.lastIndexOf("/") + 1) : "";
  const getAll = (tag: string): string[] => {
    const re = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "g");
    const out: string[] = [];
    let match: RegExpExecArray | null;
    while ((match = re.exec(xml))) out.push(decodeEntities(match[1].trim()));
    return out;
  };

  const metadata: Record<string, string[]> = {
    title: getAll("dc:title"),
    creator: getAll("dc:creator"),
    description: getAll("dc:description"),
    language: getAll("dc:language"),
    publisher: getAll("dc:publisher"),
    identifier: getAll("dc:identifier"),
  };

  const manifest: SpineEntry[] = [];
  const itemRe = /<item\s+([^>]+?)\/?>/g;
  let itemMatch: RegExpExecArray | null;
  while ((itemMatch = itemRe.exec(xml))) {
    const attrs = itemMatch[1];
    const id = /id="([^"]+)"/.exec(attrs)?.[1];
    const href = /href="([^"]+)"/.exec(attrs)?.[1];
    const mediaType = /media-type="([^"]+)"/.exec(attrs)?.[1] ?? "";
    if (id && href) manifest.push({ id, href, mediaType });
  }

  const spine: string[] = [];
  const spineMatch = /<spine[^>]*>([\s\S]*?)<\/spine>/.exec(xml);
  if (spineMatch) {
    const refRe = /<itemref\s+idref="([^"]+)"/g;
    let refMatch: RegExpExecArray | null;
    while ((refMatch = refRe.exec(spineMatch[1]))) spine.push(refMatch[1]);
  }

  return { metadata, manifest, spine, opfDir };
}

function resolvePath(base: string, rel: string): string {
  const stack = base.split("/");
  stack.pop();
  const parts = rel.split("/");
  for (const part of parts) {
    if (part === "..") stack.pop();
    else if (part !== "." && part !== "") stack.push(part);
  }
  return stack.join("/");
}

function findChapterNumber(input: { href: string; html: string }): number {
  const href = (input.href || "").toLowerCase();
  const byHref = /chapter[_\-\s]*(\d+)/.exec(href);
  if (byHref) return parseInt(byHref[1], 10);

  const headingMatch = /<h[1-3][^>]*>([\s\S]*?)<\/h[1-3]>/i.exec(input.html);
  if (headingMatch) {
    const heading = headingMatch[1].replace(/<[^>]+>/g, "").trim();
    const byHeading = /chapter[_\-\s]*(\d+)/i.exec(heading);
    if (byHeading) return parseInt(byHeading[1], 10);
  }

  return Number.MAX_SAFE_INTEGER;
}

function extractTitle(html: string, fallback: string): string {
  const headingMatch = /<h[1-3][^>]*>([\s\S]*?)<\/h[1-3]>/i.exec(html);
  if (headingMatch) {
    const text = headingMatch[1].replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
    if (text) return text;
  }

  const titleMatch = /<title>([\s\S]*?)<\/title>/i.exec(html);
  if (titleMatch) {
    const title = titleMatch[1].replace(/<[^>]+>/g, "").trim();
    if (title) return title;
  }

  return fallback;
}

function sanitizeFilename(name: string, fallback: string): string {
  return ((name || fallback).replace(/[\\/:*?"<>|]+/g, "_").slice(0, 120) || fallback);
}

export async function parseEpub(file: File | Blob): Promise<ImportedBook> {
  const zip = await JSZip.loadAsync(file);
  const { opfPath } = await parseContainer(zip);
  const { metadata, manifest, spine, opfDir } = await readOpf(zip, opfPath);

  const manifestMap = new Map(manifest.map((entry) => [entry.id, entry]));
  const chapters: ImportedChapter[] = [];
  let order = 0;

  for (const spineId of spine) {
    const item = manifestMap.get(spineId);
    if (!item) continue;
    if (!item.mediaType.includes("xhtml") && !item.mediaType.includes("html")) continue;

    const fullPath = resolvePath(opfDir, item.href);
    const entry = zip.file(fullPath);
    if (!entry) continue;

    const html = await entry.async("string");
    if (!html || html.length < 50) continue;

    const number = findChapterNumber({ href: item.href, html });
    const title = extractTitle(html, `Capítulo ${order + 1}`);
    const content = htmlToMarkdown(html);
    if (!content) continue;

    order++;
    chapters.push({
      id: `chapter-${order}`,
      title: sanitizeFilename(title, `Capítulo ${order}`),
      content,
      order: number === Number.MAX_SAFE_INTEGER ? order : number,
    });
  }

  chapters.sort((a, b) => a.order - b.order);
  if (chapters.length === 0) throw new Error("No se encontraron capítulos legibles en el EPUB.");

  return {
    title: metadata.title?.[0] || (file instanceof File ? file.name.replace(/\.epub$/i, "") : "Libro importado"),
    author: metadata.creator?.[0] || "Desconocido",
    description: metadata.description?.[0] || "",
    language: metadata.language?.[0] || "es",
    chapters,
  };
}

function normalizePotentialChapterTitle(line: string): string {
  return line.trim().replace(/^\uFEFF/, "").replace(/^#{1,6}\s+/, "").replace(/\s+#{1,6}\s*$/, "").trim();
}

function extractChapterNumberFromTitle(title: string): number | null {
  const normalized = normalizePotentialChapterTitle(title);
  if (!normalized) return null;

  const chapterNumberRegex = /^(?:cap[ií]tulo|chapter|chap|ch)\b[\s.:_-]*(\d+)\b/i;
  const chapterMatch = chapterNumberRegex.exec(normalized);
  if (chapterMatch) return Number(chapterMatch[1]);

  const numberedTitleRegex = /^(\d+)[.)]\s+(.+)$/;
  const numberedMatch = numberedTitleRegex.exec(normalized);
  if (numberedMatch) return Number(numberedMatch[1]);

  return null;
}

function extractChapterTitleFromLine(line: string): string | null {
  const normalized = normalizePotentialChapterTitle(line);
  if (!normalized) return null;

  const chapterTitleRegex = /^(?:cap[ií]tulo|chapter|chap|ch)\b[\s.:_-]*.+$/i;
  if (chapterTitleRegex.test(normalized)) return normalized;

  const numberedTitleRegex = /^(\d+)[.)]\s+(.+)$/;
  const numberedMatch = numberedTitleRegex.exec(normalized);
  if (numberedMatch) return `${numberedMatch[1]}. ${numberedMatch[2].trim()}`;

  return null;
}

export async function readTxtChapters(file: File): Promise<ImportedChapter[]> {
  const text = await file.text();
  const normalized = text.replace(/\r\n/g, "\n");
  const lines = normalized.split("\n");
  const result: ImportedChapter[] = [];
  let current: { title: string; lines: string[]; detectedOrder: number | null } | null = null;
  let index = 0;

  const pushCurrent = () => {
    if (!current) return;
    index++;
    result.push({
      id: `chapter-${index}`,
      title: current.title || `Capítulo ${index}`,
      content: current.lines.join("\n").trim(),
      order: current.detectedOrder ?? index,
    });
  };

  for (const line of lines) {
    const title = extractChapterTitleFromLine(line);
    if (title) {
      pushCurrent();
      current = { title, lines: [], detectedOrder: extractChapterNumberFromTitle(title) };
      continue;
    }

    if (!current) {
      if (!line.trim()) continue;
      current = { title: "Capítulo 1", lines: [], detectedOrder: 1 };
    }
    current.lines.push(line);
  }
  pushCurrent();

  if (result.length === 0) {
    result.push({
      id: "chapter-1",
      title: file.name.replace(/\.(txt|md)$/i, ""),
      content: normalized.trim(),
      order: 1,
    });
  }

  return [...result].sort((a, b) => a.order - b.order);
}
