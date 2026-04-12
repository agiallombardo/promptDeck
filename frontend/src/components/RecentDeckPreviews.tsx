import { useQueries } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { apiPresentationEmbed, apiPresentationGet, iframeSrcForDev } from "../lib/api";
import { removeRecentDeck, type RecentDeckEntry } from "../lib/recentDecks";

type Props = {
  accessToken: string;
  entries: RecentDeckEntry[];
};

export function RecentDeckPreviews({ accessToken, entries }: Props) {
  const presQueries = useQueries({
    queries: entries.map((e) => ({
      queryKey: ["presentation", e.id, accessToken],
      queryFn: () => apiPresentationGet(accessToken, e.id),
      enabled: Boolean(accessToken) && entries.length > 0,
      retry: false,
    })),
  });

  const embedQueries = useQueries({
    queries: entries.map((e, i) => ({
      queryKey: [
        "presentation-embed",
        e.id,
        accessToken,
        presQueries[i]?.data?.current_version_id ?? null,
      ],
      queryFn: () => apiPresentationEmbed(accessToken, e.id),
      enabled:
        Boolean(accessToken) &&
        Boolean(presQueries[i]?.data?.current_version_id) &&
        presQueries[i]?.isSuccess === true,
    })),
  });

  useEffect(() => {
    for (let i = 0; i < entries.length; i++) {
      if (presQueries[i]?.isError) {
        removeRecentDeck(entries[i].id);
      }
    }
  }, [entries, presQueries]);

  if (!entries.length) {
    return null;
  }

  return (
    <div className="mt-8">
      <h2 className="font-mono text-sm uppercase tracking-wide text-text-muted">Recently opened</h2>
      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        {entries.map((entry, i) => {
          const pres = presQueries[i];
          const embed = embedQueries[i];
          const title = pres?.data?.title ?? entry.title;
          const err = pres?.isError === true;
          const iframeSrc =
            embed?.data?.iframe_src != null && embed.data.iframe_src !== ""
              ? iframeSrcForDev(embed.data.iframe_src)
              : "";

          return (
            <Link
              key={entry.id}
              to={`/p/${entry.id}`}
              className="group block rounded-sharp outline-none ring-primary focus-visible:ring-2"
            >
              <div className="aspect-video overflow-hidden rounded-sharp border border-border bg-bg-recessed shadow-elevated transition group-hover:border-primary/40">
                {err ? (
                  <div className="flex h-full items-center justify-center px-2 text-center font-mono text-[10px] text-text-muted">
                    Unavailable
                  </div>
                ) : pres?.isLoading ? (
                  <div className="flex h-full items-center justify-center font-mono text-[10px] text-text-muted">
                    …
                  </div>
                ) : iframeSrc ? (
                  <iframe
                    title={`Preview: ${title}`}
                    src={iframeSrc}
                    sandbox="allow-scripts allow-same-origin"
                    loading="lazy"
                    className="pointer-events-none h-full w-full border-0"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center font-mono text-[10px] text-text-muted">
                    No version yet
                  </div>
                )}
              </div>
              <p
                className="mt-1.5 truncate font-mono text-[11px] text-text-muted group-hover:text-primary"
                title={title}
              >
                {title}
              </p>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
