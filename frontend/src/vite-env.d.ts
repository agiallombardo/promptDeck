/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Dev-only: force signed asset iframe URLs to this origin (must match the shell page origin). */
  readonly VITE_DEV_EMBED_ORIGIN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
