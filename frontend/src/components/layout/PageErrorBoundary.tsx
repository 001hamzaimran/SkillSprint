import { Component, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';

export class PageErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <section role="alert" className="bg-white border border-border rounded-xl p-6 space-y-4">
          <h1 className="text-xl font-semibold">This page couldn’t be displayed</h1>
          <p>Try opening it again, or choose another page from the sidebar.</p>
          <Button onClick={() => this.setState({ failed: false })}>Try again</Button>
        </section>
      );
    }
    return this.props.children;
  }
}
