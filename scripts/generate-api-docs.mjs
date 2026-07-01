#!/usr/bin/env node
/**
 * Generates a single comprehensive file documenting all API endpoints
 * consumed by the UI.
 *
 * Usage: node scripts/generate-api-docs.mjs
 * Output: docs/api-endpoints.md
 */

import { readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUTPUT = resolve(__dirname, "..", "docs/api-endpoints.md");

function read(file) {
  return readFileSync(resolve(__dirname, "..", file), "utf-8");
}

function sanitizePath(path) {
  let p = path
    // Remove URLSearchParams suffixes like `?${suffix.toString()}`
    .replace(/\?.*\$?\{?\w*\}?/g, "")
    .replace(/\$\{encodeURIComponent\((\w+)\)\}/g, ":$1")
    .replace(/\$\{(?:input\.)?(\w+)\}/g, ":$1")
    .replace(/:suffix$/, "")
    .replace(/:\w+\?$/, ":id");
  return p;
}

// ---- Extract endpoints by splitting the return object ----

function extractEndpoints(source) {
  const endpoints = [];

  // Find the main `return {` block (inside createApiClient)
  // The first `return {` is inside normalizeNovel; we want the one in createApiClient
  const apiClientStart = source.indexOf("export function createApiClient");
  if (apiClientStart === -1) return [];
  const returnStart = source.indexOf("return {", apiClientStart);
  if (returnStart === -1) return [];

  const body = source.slice(returnStart + 8); // skip "return {"
  
  // Split into top-level namespace sections by finding `name: {` at the top level
  // We do this by tracking brace depth
  
  let depth = 0;
  let currentNS = "";
  let currentSection = "";
  const sections = []; // [{ namespace, content }]

  for (let i = 0; i < body.length; i++) {
    const ch = body[i];

    // Skip strings
    if (ch === '"' || ch === "'" || ch === "`") {
      const quote = ch;
      let end = i + 1;
      while (end < body.length && body[end] !== quote) {
        if (body[end] === "\\") end++;
        end++;
      }
      if (depth >= 0) currentSection += body.slice(i, end + 1);
      i = end;
      continue;
    }

    if (ch === "{") {
      depth++;
      if (depth === 1) {
        // First-level brace inside return {} → namespace opening
        const before = currentSection.trimEnd();
        const lastLineStart = before.lastIndexOf("\n") + 1;
        const lastLine = before.slice(lastLineStart).trim();
        const nsMatch = lastLine.match(/^(\w+):\s*$/);
        if (nsMatch) {
          currentNS = nsMatch[1];
        }
      }
      if (depth >= 0) currentSection += ch;
      continue;
    }

    if (ch === "}") {
      // Namespace closing: we were at depth 1 and currentNS is set
      if (depth === 1 && currentNS) {
        currentSection += ch;
        sections.push({ namespace: currentNS, content: currentSection });
        currentSection = "";
        currentNS = "";
        depth--;
        continue;
      }
      depth--;
      if (depth >= 0) currentSection += ch;
      continue;
    }

    if (depth >= 0) {
      currentSection += ch;
    }
  }

  // Now extract http calls from each section
  for (const section of sections) {
    const ns = section.namespace;
    const content = section.content;

    // Find all http.method calls within this section
    const httpRe = /http\.(get|post|put|patch|delete)\s*(?:<\s*([^>]+)\s*>)?\s*\(/g;
    let match;

    while ((match = httpRe.exec(content)) !== null) {
      const httpMethod = match[1].toUpperCase();
      const responseType = (match[2] || "").trim();

      // Read arguments until matching )
      let j = match.index + match[0].length;
      let parenDepth = 1;
      let args = "";
      
      while (j < content.length && parenDepth > 0) {
        if (content[j] === "(") parenDepth++;
        if (content[j] === ")") parenDepth--;
        if (parenDepth > 0) {
          if (content[j] === '"' || content[j] === "'" || content[j] === "`") {
            const q = content[j];
            args += content[j];
            j++;
            while (j < content.length && content[j] !== q) {
              if (content[j] === "\\") { args += content[j]; j++; }
              args += content[j];
              j++;
            }
            args += content[j];
          } else {
            args += content[j];
          }
        }
        j++;
      }

      // Extract the first string/template argument (the path)
      const pathMatch = args.match(/^\s*(`[^`]*`|"[^"]*"|'[^']*')/);
      let path = "";
      if (pathMatch) {
        const raw = pathMatch[1];
        path = sanitizePath(raw.slice(1, -1));
      }

      if (!path) continue; // skip if no path found

      // Find the method name by walking backwards within this section
      const beforeHttp = content.slice(0, match.index);
      const beforeLines = beforeHttp.split("\n");

      let methodName = "";
      let methodParams = "";

      // Walk backwards from the http call to find the enclosing method
      for (let k = beforeLines.length - 1; k >= 0; k--) {
        const line = beforeLines[k];
        const methodMatch = line.match(
          /^\s*(?:async\s+)?(\w+)\s*(?::\s*(?:\w+(?:<[^>]+>)?\s*(?:=>\s*)?)?)?\(([^)]*)\)\s*(?::\s*\w+(?:<[^>]+>)?)?\s*\{\s*$/,
        );
        if (methodMatch) {
          methodName = methodMatch[1];
          methodParams = methodMatch[2].trim();
          break;
        }
        // Handle multi-line method definition
        const multiMatch = line.match(
          /^\s*(?:async\s+)?(\w+)\s*(?::\s*(?:\w+(?:<[^>]+>)?\s*(?:=>\s*)?)?)?\(/,
        );
        if (multiMatch && !line.includes(")")) {
          // Check if the closing `) {` is on a subsequent line (before the http call)
          // Actually, this is getting complex; just look for the method name on the line
          methodName = multiMatch[1];
          break;
        }
      }

      // Clean up the remaining args for display
      let restArgs = args.slice(pathMatch ? pathMatch[0].length : 0).trim();
      restArgs = restArgs.replace(/^,?\s*/, "").replace(/,\s*$/, "").trim();

      let bodyDisplay = "";
      if (restArgs) {
        if (restArgs.includes("new FormData") || restArgs.includes("FormData") || restArgs.startsWith("form")) {
          bodyDisplay = "FormData (multipart/form-data)";
        } else {
          bodyDisplay = restArgs.length > 150 ? restArgs.slice(0, 150) + "..." : restArgs;
        }
      }

      endpoints.push({
        methodName: methodName || "",
        namespace: ns,
        httpMethod,
        path,
        params: methodParams,
        bodyInfo: bodyDisplay,
        responseType: responseType || "unknown",
      });
    }
  }

  // Deduplicate
  const seen = new Set();
  const unique = [];
  for (const ep of endpoints) {
    const key = `${ep.namespace}|${ep.methodName}|${ep.httpMethod}|${ep.path}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(ep);
    }
  }

  unique.sort((a, b) => {
    if (a.namespace !== b.namespace) return a.namespace.localeCompare(b.namespace);
    if (a.path !== b.path) return a.path.localeCompare(b.path);
    return a.methodName.localeCompare(b.methodName);
  });

  return unique;
}

// ---- Type parsing ----

function parseInterfaces(source) {
  const types = {};
  const blocks = source.split(/(?:^|\n)(?:export\s+)?(?:type|interface)\s+/);
  for (const block of blocks) {
    const m1 = block.match(/^(\w+)(?:<\s*[^>]+\s*>)?\s*=\s*\{([\s\S]*?)\}\s*;?$/m);
    const m2 = block.match(/^(\w+)(?:<\s*[^>]+\s*>)?\s*\{([\s\S]*?)\}\s*;?$/m);
    const match = m1 || m2;
    if (match) {
      const name = match[1];
      const body = match[2].trim();
      if (!body) continue;
      const fields = [];
      const fieldRe = /^\s*(?:readonly\s+)?(\w+)\??\s*(:\s*[^;]+)?(?=;|$)/gm;
      let f;
      while ((f = fieldRe.exec(body)) !== null) {
        const typeStr = (f[2] || "").replace(/^:\s*/, "").trim();
        fields.push({ name: f[1], type: typeStr || "any" });
      }
      types[name] = fields;
    }
  }
  return types;
}

function findReferencedTypes(typeStr, allTypes) {
  const results = [];
  const seen = new Set();
  const candidates = typeStr.split(/\||&/).map((s) =>
    s.trim().replace(/\[\]$/, "").replace(/<.+>/, ""),
  );
  for (const c of candidates) {
    if (allTypes[c] && !seen.has(c)) {
      seen.add(c);
      results.push({ name: c, fields: allTypes[c] });
    }
  }
  const genericMatch = typeStr.match(/^(\w+)<(.+)>$/);
  if (genericMatch) {
    const base = genericMatch[1];
    if (allTypes[base] && !seen.has(base)) {
      seen.add(base);
      results.push({ name: base, fields: allTypes[base] });
    }
  }
  return results;
}

// ---- Main ----

const clientSrc = read("server/frontend/src/api/client.ts");
const endpoints = extractEndpoints(clientSrc);

const allTypes = {
  ...parseInterfaces(read("server/frontend/src/api/types.ts")),
  ...parseInterfaces(read("server/frontend/src/domain/index.ts")),
  ...parseInterfaces(read("server/frontend/src/domain/project-settings.ts")),
};

const lines = [];

lines.push("# API Endpoints — Novel Translator");
lines.push("");
lines.push("> Archivo generado automáticamente. Describe todas las peticiones API gestionadas desde la UI.");
lines.push("");
lines.push(`Generado el: ${new Date().toISOString().slice(0, 10)}`);
lines.push("");
lines.push(`Total de endpoints documentados: **${endpoints.length}**`);
lines.push("");
lines.push("---");
lines.push("");

const grouped = {};
for (const ep of endpoints) {
  if (!grouped[ep.namespace]) grouped[ep.namespace] = [];
  grouped[ep.namespace].push(ep);
}

for (const [ns, eps] of Object.entries(grouped)) {
  lines.push(`## ${ns.charAt(0).toUpperCase() + ns.slice(1)}`);
  lines.push("");

  for (const ep of eps) {
    lines.push(`### ${ep.httpMethod} \`${ep.path}\``);
    lines.push("");
    if (ep.methodName) {
      lines.push(`**Método en cliente:** \`api.${ep.namespace}.${ep.methodName}()\``);
      lines.push("");
      const desc = ep.methodName
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (c) => c.toUpperCase())
        .trim();
      lines.push(`**Descripción:** ${desc}`);
      lines.push("");
    }

    if (ep.bodyInfo) {
      lines.push("**Cuerpo de la petición:**");
      lines.push("```typescript");
      lines.push(ep.bodyInfo);
      lines.push("```");
      lines.push("");
    }

    if (ep.responseType && ep.responseType !== "void" && ep.responseType !== "unknown") {
      lines.push("**Tipo de respuesta:**");
      lines.push("```typescript");
      lines.push(ep.responseType);
      lines.push("```");
      lines.push("");

      const refs = findReferencedTypes(ep.responseType, allTypes);
      for (const ref of refs) {
        if (ref.fields.length > 0) {
          lines.push(`**Estructura \`${ref.name}\`:**`);
          lines.push("```typescript");
          lines.push(`type ${ref.name} = {`);
          for (const f of ref.fields) {
            lines.push(`  ${f.name}${f.type ? `: ${f.type}` : ""};`);
          }
          lines.push("};");
          lines.push("```");
          lines.push("");
        }
      }
    }

    lines.push("---");
    lines.push("");
  }
}

// Shared types
lines.push("## Tipos Compartidos (Enums)");
lines.push("");
lines.push("### ChapterStatus");
lines.push("```typescript");
lines.push('type ChapterStatus = "pending" | "processing" | "translated" | "refined" | "done" | "failed";');
lines.push("```");
lines.push("");
lines.push("### TranslationJobStatus");
lines.push("```typescript");
lines.push('type TranslationJobStatus = "pending" | "running" | "done" | "cancelled" | "failed";');
lines.push("```");
lines.push("");
lines.push("### NovelStatus");
lines.push("```typescript");
lines.push('type NovelStatus = "ongoing" | "completed" | "hiatus" | "cancelled";');
lines.push("```");
lines.push("");

writeFileSync(OUTPUT, lines.join("\n"), "utf-8");
console.log(`✓ API endpoints documentation generated: ${OUTPUT}`);
console.log(`  Total endpoints: ${endpoints.length}`);
for (const ep of endpoints) {
  console.log(`  ${ep.httpMethod} ${ep.path}  (${ep.namespace}.${ep.methodName})`);
}
