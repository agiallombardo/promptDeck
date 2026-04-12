import {
  DECK_PROMPT_TEMPLATES_EDIT_DECK,
  DECK_PROMPT_TEMPLATES_NEW_DECK,
} from "../lib/deckPromptTemplates";

type Props = {
  onPick: (body: string) => void;
  disabled?: boolean;
  className?: string;
  /** New-deck flow vs editing an existing deck */
  variant?: "new_deck" | "edit_deck";
};

export function DeckPromptTemplateChips({
  onPick,
  disabled,
  className,
  variant = "new_deck",
}: Props) {
  const list =
    variant === "edit_deck" ? DECK_PROMPT_TEMPLATES_EDIT_DECK : DECK_PROMPT_TEMPLATES_NEW_DECK;
  return (
    <div className={className ?? "flex flex-wrap gap-2"}>
      {list.map((t) => (
        <button
          key={t.id}
          type="button"
          disabled={disabled}
          onClick={() => onPick(t.body)}
          className="rounded-sharp border border-border bg-bg-recessed px-2.5 py-1 font-mono text-[11px] text-text-muted hover:border-primary/40 hover:text-text-main disabled:opacity-50"
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
