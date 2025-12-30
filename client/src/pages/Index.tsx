import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import Sidebar from '@/components/Sidebar';
import Dashboard from '@/components/Dashboard';
import PoliticiansView from '@/components/PoliticiansView';
import FilingsView from '@/components/FilingsView';
// COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready
// import TradingSignals from '@/pages/TradingSignals';
// import TradingOperations from '@/pages/TradingOperations';
// import Portfolio from '@/pages/Portfolio';
// import Orders from '@/pages/Orders';
// import ScheduledJobs from '@/pages/ScheduledJobs';
// import TradesView from '@/components/TradesView';

const Index = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('dashboard');
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string | undefined>(undefined);

  const [searchQuery, setSearchQuery] = useState('');

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

  const renderContent = () => {
    switch (activeSection) {
      case 'politicians':
        return <PoliticiansView jurisdictionId={selectedJurisdiction} />;
      case 'filings':
        return <FilingsView jurisdictionId={selectedJurisdiction} />;
      // COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready
      // case 'trading-signals':
      //   return <TradingSignals />;
      // case 'trading-operations':
      //   return <TradingOperations />;
      // case 'portfolio':
      //   return <Portfolio />;
      // case 'orders':
      //   return <Orders />;
      // case 'scheduled-jobs':
      //   return <ScheduledJobs />;
      // case 'trades':
      //   return <TradesView jurisdictionId={selectedJurisdiction} searchQuery={searchQuery} />;
      default:
        return <Dashboard jurisdictionId={selectedJurisdiction} />;
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
          onSectionChange={setActiveSection}
          selectedJurisdiction={selectedJurisdiction}
          onJurisdictionChange={setSelectedJurisdiction}
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
