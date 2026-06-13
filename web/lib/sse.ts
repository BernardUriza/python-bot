/** Parse one SSE frame ("event: foo\ndata: {...}") into {event, data}.
 * Frames are separated by \n\n — the caller splits on that first. */
export function parseSseFrame(frame: string): { event: string; data: unknown } | null {
  const lines = frame.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}
