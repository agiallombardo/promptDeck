import { Link } from "react-router-dom";

type Props = {
  /** When true, shows the wordmark beside the icon (app shell). */
  showWordmark?: boolean;
};

const imgClass =
  "h-7 w-7 shrink-0 opacity-90 hover:opacity-100";

const linkClass =
  "shrink-0 rounded-sharp outline-none ring-primary focus-visible:ring-2";

export function PromptDeckHomeLink({ showWordmark = false }: Props) {
  return (
    <Link
      to="/files"
      className={
        showWordmark ? `${linkClass} inline-flex items-center gap-2` : linkClass
      }
      title="Home"
      aria-label="Home — file manager"
    >
      <img
        src="/favicon.svg"
        alt=""
        width={28}
        height={28}
        className={imgClass}
      />
      {showWordmark ? (
        <span className="font-mono text-xs uppercase tracking-wide text-primary">
          promptDeck
        </span>
      ) : null}
    </Link>
  );
}
