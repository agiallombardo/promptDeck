import { DECK_PROMPT_TEMPLATES } from "../lib/deckPromptTemplates";

type Props = {
  onPick: (body: string) => void;
  disabled?: boolean;
  className?: string;
};

export function DeckPromptTemplateChips({ onPick, disabled, className }: Props) {
  return (
    <div className={className ?? "flex flex-wrap gap-2"}>
      {DECK_PROMPT_TEMPLATES.map((t) => (
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
