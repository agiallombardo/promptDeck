import { Link } from "react-router-dom";

export default function App() {
  return (
    <div className="min-h-dvh bg-bg-void text-text-main font-body antialiased">
      <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-16">
        <p className="font-mono text-sm text-primary">PresCollab · M1</p>
        <h1 className="font-heading text-3xl font-semibold tracking-tight text-text-main">
          Presentation canvas
        </h1>
        <p className="text-text-muted">
          Upload HTML decks, review with pinned comments, export to PDF — v1 build in progress.
        </p>
        <nav className="flex flex-wrap gap-4 font-mono text-sm">
          <Link className="text-primary underline decoration-primary/40" to="/login">
            Sign in
          </Link>
          <Link className="text-primary underline decoration-primary/40" to="/files">
            Files
          </Link>
          <Link className="text-primary underline decoration-primary/40" to="/admin">
            Admin logs
          </Link>
        </nav>
      </main>
    </div>
  );
}
