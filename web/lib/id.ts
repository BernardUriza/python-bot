/** Mint a short id without depending on `crypto.randomUUID` (Safari 14 etc.). */
export function newId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
