import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiMeSettingsGet, apiMeSettingsPatch } from "../lib/api";
import { useAuthStore } from "../stores/auth";

export default function SettingsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  const [provider, setProvider] = useState("");
  const [apiKey, setApiKey] = useState("");

  const settings = useQuery({
    queryKey: ["me", "settings", accessToken],
    enabled: Boolean(accessToken),
    queryFn: () => apiMeSettingsGet(accessToken!),
  });

  useEffect(() => {
    if (settings.data) {
      setProvider(settings.data.llm_provider ?? "");
    }
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () =>
      apiMeSettingsPatch(accessToken!, {
        llm_provider: provider.trim() ? provider.trim() : null,
        ...(apiKey.trim() ? { llm_api_key: apiKey.trim() } : {}),
        clear_llm_api_key: false,
      }),
    onSuccess: async () => {
      setApiKey("");
      await qc.invalidateQueries({ queryKey: ["me", "settings", accessToken] });
    },
  });

  const clearKey = useMutation({
    mutationFn: () =>
      apiMeSettingsPatch(accessToken!, {
        llm_provider: provider.trim() ? provider.trim() : null,
        clear_llm_api_key: true,
      }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["me", "settings", accessToken] });
    },
  });

  const fieldClass =
    "w-full max-w-md rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-mono text-sm text-text-main outline-none ring-primary focus:ring-1";

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 text-text-main">
      <p className="font-mono text-sm text-primary">Account</p>
      <h1 className="font-heading text-3xl font-semibold">Settings</h1>
      <p className="mt-2 text-sm text-text-muted">
        LLM provider and API key are stored encrypted on the server for future features. The key is
        never shown again after you save.
      </p>

      {settings.isLoading ? (
        <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
      ) : settings.isError ? (
        <p className="mt-10 text-accent-warning" role="alert">
          {(settings.error as Error).message}
        </p>
      ) : (
        <div className="mt-8 space-y-6 rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated">
          <label className="grid gap-1 font-mono text-xs">
            <span className="text-text-muted">LLM provider (optional)</span>
            <input
              className={fieldClass}
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              placeholder="e.g. openai"
              maxLength={64}
            />
          </label>

          <div className="grid gap-1 font-mono text-xs">
            <span className="text-text-muted">API key</span>
            <input
              className={fieldClass}
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                settings.data?.llm_api_key_configured
                  ? "Enter a new key to replace the stored one"
                  : "Paste API key to store"
              }
            />
            <p className="mt-1 text-text-muted">
              Status:{" "}
              {settings.data?.llm_api_key_configured ? (
                <span className="text-primary">Key on file</span>
              ) : (
                <span>No key stored</span>
              )}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-xs text-primary ring-1 ring-primary/40 disabled:opacity-50"
              disabled={save.isPending || clearKey.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="rounded-sharp border border-border px-4 py-2 font-mono text-xs hover:bg-bg-recessed disabled:opacity-50"
              disabled={
                clearKey.isPending || save.isPending || !settings.data?.llm_api_key_configured
              }
              onClick={() => clearKey.mutate()}
            >
              {clearKey.isPending ? "Clearing…" : "Clear API key"}
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
