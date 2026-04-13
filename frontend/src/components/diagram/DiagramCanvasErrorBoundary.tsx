import { Component, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  onError?: (message: string) => void;
};

type State = {
  hasError: boolean;
  message: string | null;
};

export class DiagramCanvasErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: null };

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : "Diagram renderer failed",
    };
  }

  componentDidCatch(error: unknown): void {
    const msg = error instanceof Error ? error.message : "Diagram renderer failed";
    this.props.onError?.(msg);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex h-full min-h-[280px] items-center justify-center rounded-sharp border border-accent-warning/40 bg-bg-recessed p-6 text-center">
          <p className="max-w-md font-mono text-xs text-accent-warning">
            Diagram could not render safely. Reload the page or restore a previous version.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
