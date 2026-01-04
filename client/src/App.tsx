import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { WalletProvider } from "@/components/WalletProvider";
import { CartProvider } from "@/contexts/CartContext";
import { AlertProvider } from "@/contexts/AlertContext";
import { FloatingCart } from "@/components/cart";
import { RootErrorBoundary } from "@/components/RootErrorBoundary";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import SignalPlayground from "./pages/SignalPlayground";
import Showcase from "./pages/Showcase";
import Trading from "./pages/Trading";
import TradingSignals from "./pages/TradingSignals";
import DataQuality from "./pages/DataQuality";
import ReferencePortfolio from "./pages/ReferencePortfolio";
// COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready
// import Admin from "./pages/Admin";
// import AdminDataCollection from "./pages/AdminDataCollection";
// import Settings from "./pages/Settings";
// import Subscription from "./pages/Subscription";
import NotFound from "./pages/NotFound";

const App = () => (
  <RootErrorBoundary>
    <WalletProvider>
      <AlertProvider>
        <CartProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              <Route path="/" element={
                <ErrorBoundary name="Dashboard">
                  <Index />
                </ErrorBoundary>
              } />
              <Route path="/auth" element={
                <ErrorBoundary name="Authentication">
                  <Auth />
                </ErrorBoundary>
              } />
              <Route path="/playground" element={
                <ErrorBoundary name="Signal Playground">
                  <SignalPlayground />
                </ErrorBoundary>
              } />
              <Route path="/showcase" element={
                <ErrorBoundary name="Showcase">
                  <Showcase />
                </ErrorBoundary>
              } />
              <Route path="/trading" element={
                <ErrorBoundary name="Trading">
                  <Trading />
                </ErrorBoundary>
              } />
              <Route path="/trading-signals" element={
                <ErrorBoundary name="Trading Signals">
                  <TradingSignals />
                </ErrorBoundary>
              } />
              <Route path="/admin/data-quality" element={
                <ErrorBoundary name="Data Quality">
                  <DataQuality />
                </ErrorBoundary>
              } />
              <Route path="/reference-portfolio" element={
                <ErrorBoundary name="Reference Portfolio">
                  <ReferencePortfolio />
                </ErrorBoundary>
              } />
              {/* COMMENTED OUT FOR MINIMAL BUILD - Uncomment when ready */}
              {/* <Route path="/admin" element={<Admin />} /> */}
              {/* <Route path="/admin/data-collection" element={<AdminDataCollection />} /> */}
              {/* <Route path="/settings" element={<Settings />} /> */}
              {/* <Route path="/subscription" element={<Subscription />} /> */}
              {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
              <Route path="*" element={<NotFound />} />
            </Routes>
            <FloatingCart />
          </BrowserRouter>
          </TooltipProvider>
        </CartProvider>
      </AlertProvider>
    </WalletProvider>
  </RootErrorBoundary>
);

export default App;
