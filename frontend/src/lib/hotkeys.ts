export function shouldIgnoreDeckHotkeys(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") {
    return true;
  }
  const editableAttr = target.getAttribute("contenteditable");
  return Boolean(
    target.isContentEditable ||
    target.contentEditable?.toLowerCase() === "true" ||
    editableAttr === "" ||
    editableAttr?.toLowerCase() === "true",
  );
}
