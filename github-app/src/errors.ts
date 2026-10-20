/**
 * Raised by stubs that are deliberately not built yet. The message always
 * names the docs/ROADMAP.md item that tracks the missing work.
 */
export class NotImplementedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotImplementedError";
  }
}
