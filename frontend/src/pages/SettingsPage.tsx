import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { components } from "../lib/api/schema";
import { apiMeSettingsGet, apiMeSettingsPatch } from "../lib/api";
import { useAuthStore } from "../stores/auth";

type DeckLlmProvider = "litellm" | "openai" | "claude";

function emptyUserSettingsPatch(): components["schemas"]["UserSettingsUpdate"] {
  return {
    clear_llm_provider: false,
    clear_openai_api_base: false,
    clear_openai_api_key: false,
    clear_anthropic_api_base: false,
    clear_anthropic_api_key: false,
    clear_litellm_api_base: false,
    clear_litellm_api_key: false,
    clear_llm_api_key: false,
  };
}

export default function SettingsPage() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const qc = useQueryClient();
  /** "" = use organization defaults only */
  const [providerChoice, setProviderChoice] = useState<string>("");
  const [openaiBase, setOpenaiBase] = useState("");
  const [anthropicBase, setAnthropicBase] = useState("");
  const [litellmBase, setLitellmBase] = useState("");
  const [openaiBaseDirty, setOpenaiBaseDirty] = useState(false);
  const [anthropicBaseDirty, setAnthropicBaseDirty] = useState(false);
  const [litellmBaseDirty, setLitellmBaseDirty] = useState(false);
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [litellmKey, setLitellmKey] = useState("");
  const [clearOpenaiKey, setClearOpenaiKey] = useState(false);
  const [clearAnthropicKey, setClearAnthropicKey] = useState(false);
  const [clearLitellmKey, setClearLitellmKey] = useState(false);
  const [clearOpenaiBase, setClearOpenaiBase] = useState(false);
  const [clearAnthropicBase, setClearAnthropicBase] = useState(false);
  const [clearLitellmBase, setClearLitellmBase] = useState(false);

  const settings = useQuery({
    queryKey: ["me", "settings", accessToken],
    enabled: Boolean(accessToken),
    queryFn: () => apiMeSettingsGet(accessToken!),
  });

  useEffect(() => {
    if (!settings.data) return;
    setProviderChoice(settings.data.llm_provider ?? "");
    setOpenaiBase(settings.data.openai_api_base ?? "");
    setAnthropicBase(settings.data.anthropic_api_base ?? "");
    setLitellmBase(settings.data.litellm_api_base ?? "");
    setOpenaiBaseDirty(false);
    setAnthropicBaseDirty(false);
    setLitellmBaseDirty(false);
    setOpenaiKey("");
    setAnthropicKey("");
    setLitellmKey("");
    setClearOpenaiKey(false);
    setClearAnthropicKey(false);
    setClearLitellmKey(false);
    setClearOpenaiBase(false);
    setClearAnthropicBase(false);
    setClearLitellmBase(false);
  }, [settings.data]);

  const save = useMutation({
    mutationFn: () => {
      const body = emptyUserSettingsPatch();
      if (providerChoice === "") {
        body.clear_llm_provider = true;
      } else {
        body.llm_provider = providerChoice as DeckLlmProvider;
      }
      if (clearOpenaiBase) body.clear_openai_api_base = true;
      else if (openaiBaseDirty) body.openai_api_base = openaiBase.trim();
      if (clearAnthropicBase) body.clear_anthropic_api_base = true;
      else if (anthropicBaseDirty) body.anthropic_api_base = anthropicBase.trim();
      if (clearLitellmBase) body.clear_litellm_api_base = true;
      else if (litellmBaseDirty) body.litellm_api_base = litellmBase.trim();
      if (clearOpenaiKey) body.clear_openai_api_key = true;
      else if (openaiKey.trim()) body.openai_api_key = openaiKey.trim();
      if (clearAnthropicKey) body.clear_anthropic_api_key = true;
      else if (anthropicKey.trim()) body.anthropic_api_key = anthropicKey.trim();
      if (clearLitellmKey) body.clear_litellm_api_key = true;
      else if (litellmKey.trim()) body.litellm_api_key = litellmKey.trim();
      return apiMeSettingsPatch(accessToken!, body);
    },
    onSuccess: async () => {
      setOpenaiKey("");
      setAnthropicKey("");
      setLitellmKey("");
      await qc.invalidateQueries({ queryKey: ["me", "settings", accessToken] });
    },
  });

  const fieldClass =
    "w-full max-w-md rounded-sharp border border-border bg-bg-recessed px-2 py-2 font-mono text-sm text-text-main outline-none ring-primary focus:ring-1";

  const selected = providerChoice as DeckLlmProvider | "";

  return (
    <main className="mx-auto max-w-2xl px-4 py-10 text-text-main">
      <p className="font-mono text-sm text-primary">Account</p>
      <h1 className="font-heading text-3xl font-semibold">Settings</h1>
      <p className="mt-2 text-sm text-text-muted">
        Optional personal LLM credentials override the organization defaults for AI deck edits. Keys
        are encrypted on the server and never shown again after you save.
      </p>

      {settings.isLoading ? (
        <p className="mt-10 font-mono text-sm text-text-muted">Loading…</p>
      ) : settings.isError ? (
        <p className="mt-10 text-accent-warning" role="alert">
          {(settings.error as Error).message}
        </p>
      ) : (
        <div className="mt-8 space-y-6 rounded-sharp border border-border bg-bg-elevated p-6 shadow-elevated">
          <div className="rounded-sharp border border-border bg-bg-recessed p-3 font-mono text-xs">
            <p className="text-text-muted">Session</p>
            <p className="mt-1 text-text-main">
              {user?.email ?? "Unknown user"} · role {user?.role ?? "user"} · provider{" "}
              {user?.auth_provider ?? "local"}
            </p>
            <p className="mt-2 text-text-muted">
              Sessions auto-refresh via secure HttpOnly cookies and idle sign-out runs after 4 hours
              of inactivity.
            </p>
          </div>

          <label className="grid gap-1 font-mono text-xs">
            <span className="text-text-muted">LLM provider (personal override)</span>
            <select
              className={fieldClass}
              value={providerChoice}
              onChange={(e) => setProviderChoice(e.target.value)}
            >
              <option value="">Organization default</option>
              <option value="openai">OpenAI (API)</option>
              <option value="claude">Claude (Anthropic API)</option>
              <option value="litellm">LiteLLM / OpenAI-compatible (HTTP)</option>
            </select>
          </label>

          {selected === "openai" ? (
            <div className="space-y-4 rounded-sharp border border-border bg-bg-recessed p-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                OpenAI
              </p>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">API base URL (optional)</span>
                <input
                  className={fieldClass}
                  value={openaiBase}
                  onChange={(e) => {
                    setOpenaiBase(e.target.value);
                    setOpenaiBaseDirty(true);
                  }}
                  placeholder="Default: https://api.openai.com/v1"
                  autoComplete="off"
                />
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearOpenaiBase}
                  onChange={(e) => setClearOpenaiBase(e.target.checked)}
                />
                Remove saved base URL override
              </label>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">API key (write-only)</span>
                <input
                  className={fieldClass}
                  type="password"
                  autoComplete="off"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={
                    settings.data?.openai_api_key_configured
                      ? "Leave blank to keep existing key"
                      : "sk-…"
                  }
                />
                <span className="text-text-muted">
                  Status:{" "}
                  {settings.data?.openai_api_key_configured ? (
                    <span className="text-primary">Key on file</span>
                  ) : (
                    <span>No key stored</span>
                  )}
                </span>
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearOpenaiKey}
                  onChange={(e) => setClearOpenaiKey(e.target.checked)}
                />
                Remove stored OpenAI key
              </label>
            </div>
          ) : null}

          {selected === "claude" ? (
            <div className="space-y-4 rounded-sharp border border-border bg-bg-recessed p-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                Anthropic
              </p>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">API base URL (optional)</span>
                <input
                  className={fieldClass}
                  value={anthropicBase}
                  onChange={(e) => {
                    setAnthropicBase(e.target.value);
                    setAnthropicBaseDirty(true);
                  }}
                  placeholder="Default: https://api.anthropic.com"
                  autoComplete="off"
                />
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearAnthropicBase}
                  onChange={(e) => setClearAnthropicBase(e.target.checked)}
                />
                Remove saved base URL override
              </label>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">API key (write-only)</span>
                <input
                  className={fieldClass}
                  type="password"
                  autoComplete="off"
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder={
                    settings.data?.anthropic_api_key_configured
                      ? "Leave blank to keep existing key"
                      : "sk-ant-…"
                  }
                />
                <span className="text-text-muted">
                  Status:{" "}
                  {settings.data?.anthropic_api_key_configured ? (
                    <span className="text-primary">Key on file</span>
                  ) : (
                    <span>No key stored</span>
                  )}
                </span>
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearAnthropicKey}
                  onChange={(e) => setClearAnthropicKey(e.target.checked)}
                />
                Remove stored Anthropic key
              </label>
            </div>
          ) : null}

          {selected === "litellm" ? (
            <div className="space-y-4 rounded-sharp border border-border bg-bg-recessed p-4">
              <p className="font-mono text-[10px] uppercase tracking-wide text-text-muted">
                LiteLLM
              </p>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">OpenAI-compatible base URL</span>
                <input
                  className={fieldClass}
                  value={litellmBase}
                  onChange={(e) => {
                    setLitellmBase(e.target.value);
                    setLitellmBaseDirty(true);
                  }}
                  placeholder="https://litellm.example.com/v1"
                  autoComplete="off"
                />
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearLitellmBase}
                  onChange={(e) => setClearLitellmBase(e.target.checked)}
                />
                Remove saved base URL
              </label>
              <label className="grid gap-1 font-mono text-xs">
                <span className="text-text-muted">API key (optional, write-only)</span>
                <input
                  className={fieldClass}
                  type="password"
                  autoComplete="off"
                  value={litellmKey}
                  onChange={(e) => setLitellmKey(e.target.value)}
                  placeholder={
                    settings.data?.litellm_api_key_configured
                      ? "Leave blank to keep existing key"
                      : "Bearer / virtual key"
                  }
                />
                <span className="text-text-muted">
                  Status:{" "}
                  {settings.data?.litellm_api_key_configured ? (
                    <span className="text-primary">Key on file</span>
                  ) : (
                    <span>No key stored</span>
                  )}
                </span>
              </label>
              <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-text-main">
                <input
                  type="checkbox"
                  checked={clearLitellmKey}
                  onChange={(e) => setClearLitellmKey(e.target.checked)}
                />
                Remove stored LiteLLM key
              </label>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-sharp bg-primary/15 px-4 py-2 font-mono text-xs text-primary ring-1 ring-primary/40 disabled:opacity-50"
              disabled={save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save"}
            </button>
          </div>
          {save.isSuccess ? (
            <p className="text-sm text-primary" role="status">
              Settings saved.
            </p>
          ) : null}
          {save.isError ? (
            <p className="text-sm text-accent-warning" role="alert">
              {(save.error as Error).message}
            </p>
          ) : null}
        </div>
      )}
    </main>
  );
}
