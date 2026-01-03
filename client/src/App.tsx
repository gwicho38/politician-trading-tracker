import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WalletProvider } from "@/components/WalletProvider";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import SignalPlayground from "./pages/SignalPlayground";
import Showcase from "./pages/Showcase";
import Trading from "./pages/Trading";
import TradingSignals from "./pages/TradingSignals";
import DataQuality from "./pages/DataQuality";
// COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready
// import Admin from "./pages/Admin";
// import AdminDataCollection from "./pages/AdminDataCollection";
// import Settings from "./pages/Settings";
// import Subscription from "./pages/Subscription";
import NotFound from "./pages/NotFound";

const App = () => (
  <WalletProvider>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/playground" element={<SignalPlayground />} />
          <Route path="/showcase" element={<Showcase />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/trading-signals" element={<TradingSignals />} />
          <Route path="/admin/data-quality" element={<DataQuality />} />
          {/* COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready */}
          {/* <Route path="/admin" element={<Admin />} /> */}
          {/* <Route path="/admin/data-collection" element={<AdminDataCollection />} /> */}
          {/* <Route path="/settings" element={<Settings />} /> */}
          {/* <Route path="/subscription" element={<Subscription />} /> */}
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </WalletProvider>
);

export default App;
