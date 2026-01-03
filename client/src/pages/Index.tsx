import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import PoliticiansView from '@/components/PoliticiansView';
import FilingsView from '@/components/FilingsView';

const Index = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('dashboard');
  const [selectedPoliticianId, setSelectedPoliticianId] = useState<string | null>(null);
  const [tickerFilter, setTickerFilter] = useState<string | undefined>(undefined);

  const [searchQuery, setSearchQuery] = useState('');

  // Handle URL parameters on mount and when they change
  useEffect(() => {
    const view = searchParams.get('view');
    const politicianId = searchParams.get('politician');
    const ticker = searchParams.get('ticker');

    if (view) {
      setActiveSection(view);
    }
    if (politicianId) {
      setSelectedPoliticianId(politicianId);
      if (!view) setActiveSection('politicians');
    }
    if (ticker) {
      setTickerFilter(ticker);
      // Ticker search goes to dashboard (which has the trades table)
      if (!view) setActiveSection('dashboard');
    }

    // Clear URL params after processing
    if (view || politicianId || ticker) {
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Listen for navigation events from child components
  useEffect(() => {
    const handleNavigate = (e: CustomEvent<string>) => {
      setActiveSection(e.detail);
    };
    const handleSearch = (e: CustomEvent<string>) => {
      setSearchQuery(e.detail);
      setActiveSection('trades'); // Switch to trades view to show results
    };
    window.addEventListener('navigate-section', handleNavigate as EventListener);
    window.addEventListener('search', handleSearch as EventListener);
    return () => {
      window.removeEventListener('navigate-section', handleNavigate as EventListener);
      window.removeEventListener('search', handleSearch as EventListener);
    };
  }, []);

  // Clear politician selection when switching away from politicians view
  const handleSectionChange = (section: string) => {
    if (section !== 'politicians') {
      setSelectedPoliticianId(null);
    }
    if (section !== 'filings') {
      setTickerFilter(undefined);
    }
    setActiveSection(section);
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'politicians':
        return (
          <PoliticiansView
            initialPoliticianId={selectedPoliticianId}
            onPoliticianSelected={() => setSelectedPoliticianId(null)}
          />
        );
      case 'filings':
        return <FilingsView />;
      default:
        return (
          <Dashboard
            initialTickerSearch={tickerFilter}
            onTickerSearchClear={() => setTickerFilter(undefined)}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Background gradient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/3 rounded-full blur-3xl" />
      </div>

      <div className="relative flex min-h-screen">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
        />

        <div className="flex-1 flex flex-col min-h-screen">
          <Header onMenuClick={() => setSidebarOpen(true)} />

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
                <span className="mx-2">|</span>
                <a href="https://www.congress.gov/members" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">US Congress</a>
                <span className="mx-2">•</span>
                <a href="https://www.europarl.europa.eu/meps/en/home" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">EU Parliament</a>
                <span className="mx-2">•</span>
                <a href="https://www.parliament.uk/mps-lords-and-offices/mps/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">UK Parliament</a>
              </p>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default Index;
