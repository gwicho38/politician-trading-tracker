import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SidebarLayout } from '@/components/layouts/SidebarLayout';
import Dashboard from '@/components/Dashboard';
import PoliticiansView from '@/components/PoliticiansView';
import FilingsView from '@/components/FilingsView';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const Index = () => {
  const [searchParams] = useSearchParams();
  const [selectedPoliticianId, setSelectedPoliticianId] = useState<string | null>(null);
  const [tickerFilter, setTickerFilter] = useState<string | undefined>(undefined);

  // Get active section from URL params
  const view = searchParams.get('view');
  const activeSection = view || 'dashboard';

  // Handle URL parameters for politician and ticker
  useEffect(() => {
    const politicianId = searchParams.get('politician');
    const ticker = searchParams.get('ticker');

    if (politicianId) {
      setSelectedPoliticianId(politicianId);
    }
    if (ticker) {
      setTickerFilter(ticker);
    }
  }, [searchParams]);

  // Clear state when switching sections
  useEffect(() => {
    if (activeSection !== 'politicians') {
      setSelectedPoliticianId(null);
    }
    if (activeSection !== 'filings') {
      setTickerFilter(undefined);
    }
  }, [activeSection]);

  const renderContent = () => {
    switch (activeSection) {
      case 'politicians':
        return (
          <ErrorBoundary name="Politicians View" resetKeys={[activeSection]}>
            <PoliticiansView
              initialPoliticianId={selectedPoliticianId}
              onPoliticianSelected={() => setSelectedPoliticianId(null)}
            />
          </ErrorBoundary>
        );
      case 'filings':
        return (
          <ErrorBoundary name="Filings View" resetKeys={[activeSection]}>
            <FilingsView />
          </ErrorBoundary>
        );
      default:
        return (
          <ErrorBoundary name="Dashboard" resetKeys={[activeSection]}>
            <Dashboard
              initialTickerSearch={tickerFilter}
              onTickerSearchClear={() => setTickerFilter(undefined)}
            />
          </ErrorBoundary>
        );
    }
  };

  return (
    <SidebarLayout>
      {/* Background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/3 rounded-full blur-3xl" />
      </div>

      <div className="relative flex-1 flex flex-col min-h-screen">
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 scrollbar-thin">
          <div className="mx-auto max-w-7xl">
            {renderContent()}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-border/50 bg-background/50 backdrop-blur-xl py-4">
          <div className="container px-4 text-center text-sm text-muted-foreground">
            <p>
              Data sourced from official government disclosures •
              <a href="https://www.congress.gov/members" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline ml-2">US Congress</a>
            </p>
            <p className="mt-2">
              Contact: <a href="mailto:luis@lefv.io" className="text-primary hover:underline">luis@lefv.io</a>
            </p>
          </div>
        </footer>
      </div>
    </SidebarLayout>
  );
};

export default Index;
