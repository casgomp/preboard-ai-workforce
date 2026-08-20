export async function extractDocumentText(file: File) {
  if (file.size > 5 * 1024 * 1024) throw new Error("Documents must be 5 MB or smaller for this demo.");
  const extension = file.name.split(".").pop()?.toLowerCase();
  let text = "";
  if (file.type === "application/pdf" || extension === "pdf") {
    const { extractText } = await import("unpdf");
    const result = await extractText(new Uint8Array(await file.arrayBuffer()), { mergePages: true });
    text = result.text;
  } else if (["txt", "md", "csv", "json", "html", "htm"].includes(extension ?? "") || file.type.startsWith("text/") || file.type === "application/json") {
    text = await file.text();
    if (["html", "htm"].includes(extension ?? "")) text = text.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ");
  } else throw new Error("Supported formats are PDF, TXT, Markdown, CSV, JSON and HTML.");
  text = text.replace(/\r/g, "").replace(/[ \t]+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
  if (text.length < 40) throw new Error("No usable text could be extracted from this document.");
  return text;
}

export function chunkDocument(text: string, targetSize = 900) {
  const paragraphs = text.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
  const chunks: string[] = [];
  let current = "";
  for (const paragraph of paragraphs) {
    if (current && current.length + paragraph.length > targetSize) { chunks.push(current); current = paragraph; }
    else current = current ? `${current}\n\n${paragraph}` : paragraph;
  }
  if (current) chunks.push(current);
  return chunks.flatMap((chunk) => chunk.length > targetSize * 1.7 ? chunk.match(new RegExp(`.{1,${targetSize}}(?:\\s|$)`, "gs"))?.map((item) => item.trim()) ?? [chunk] : [chunk]);
}
