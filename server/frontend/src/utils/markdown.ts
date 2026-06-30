function escapeHtml(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInlineMarkdown(input: string): string {
  return input
    .replace(/\*\*\*([^*\n]+)\*\*\*/g, "<strong><em>$1</em></strong>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>")
    .replace(/_([^_\n]+)_/g, "<em>$1</em>");
}

export function markdownToHtml(markdown: string): string {
  let text = escapeHtml((markdown || "").replace(/\r\n/g, "\n"));
  text = text.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  text = text.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  text = text.replace(/^# (.*)$/gm, "<h1>$1</h1>");
  text = text.replace(/^>\s?(.*)$/gm, "<blockquote>$1</blockquote>");
  text = text.replace(/^(---|\*\*\*)\s*$/gm, "<hr/>");
  text = text.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");

  const blocks = text.split(/\n{2,}/);
  const out: string[] = [];

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    if (/^(<li>.*<\/li>(\n<li>.*<\/li>)*)$/s.test(trimmed)) {
      const items = trimmed
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .map(renderInlineMarkdown)
        .join("");
      out.push(`<ul>${items}</ul>`);
      continue;
    }

    if (/^<(h\d|blockquote|hr)/.test(trimmed)) {
      out.push(renderInlineMarkdown(trimmed));
      continue;
    }

    const withBreaks = trimmed
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map(renderInlineMarkdown)
      .join("<br/>");

    out.push(`<p>${withBreaks}</p>`);
  }

  return out.join("\n");
}
