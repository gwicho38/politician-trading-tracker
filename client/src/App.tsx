import { Suspense, lazy } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { WalletProvider } from "@/components/WalletProvider";
import { CartProvider } from "@/contexts/CartContext";
import { AlertProvider } from "@/contexts/AlertContext";
import { FloatingCart } from "@/components/cart";
import { RootErrorBoundary } from "@/components/RootErrorBoundary";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ProtectedRoute, AdminRoute } from "@/components/ProtectedRoute";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";

// Lazy-load pages with heavy dependencies (Monaco, Recharts, Web3)
// This reduces initial bundle size by ~300KB
const Auth = lazy(() => import("./pages/Auth"));
const SignalPlayground = lazy(() => import("./pages/SignalPlayground"));
const Showcase = lazy(() => import("./pages/Showcase"));
const Trading = lazy(() => import("./pages/Trading"));
const TradingSignals = lazy(() => import("./pages/TradingSignals"));
const Drops = lazy(() => import("./pages/Drops"));
const DataQuality = lazy(() => import("./pages/DataQuality"));
const ReferencePortfolio = lazy(() => import("./pages/ReferencePortfolio"));

// Loading fallback component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

const App = () => (
  <RootErrorBoundary>
    <AuthProvider>
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
                  <Suspense fallback={<PageLoader />}>
                    <Auth />
                  </Suspense>
                </ErrorBoundary>
              } />
              <Route path="/playground" element={
                <ErrorBoundary name="Signal Playground">
                  <Suspense fallback={<PageLoader />}>
                    <SignalPlayground />
                  </Suspense>
                </ErrorBoundary>
              } />
              <Route path="/showcase" element={
                <ErrorBoundary name="Showcase">
                  <Suspense fallback={<PageLoader />}>
                    <Showcase />
                  </Suspense>
                </ErrorBoundary>
              } />
              <Route path="/drops" element={
                <ErrorBoundary name="Drops">
                  <Suspense fallback={<PageLoader />}>
                    <Drops />
                  </Suspense>
                </ErrorBoundary>
              } />
              <Route path="/trading" element={
                <ErrorBoundary name="Trading">
                  <ProtectedRoute>
                    <Suspense fallback={<PageLoader />}>
                      <Trading />
                    </Suspense>
                  </ProtectedRoute>
                </ErrorBoundary>
              } />
              <Route path="/trading-signals" element={
                <ErrorBoundary name="Trading Signals">
                  <Suspense fallback={<PageLoader />}>
                    <TradingSignals />
                  </Suspense>
                </ErrorBoundary>
              } />
              <Route path="/admin/data-quality" element={
                <ErrorBoundary name="Data Quality">
                  <AdminRoute>
                    <Suspense fallback={<PageLoader />}>
                      <DataQuality />
                    </Suspense>
                  </AdminRoute>
                </ErrorBoundary>
              } />
              <Route path="/reference-portfolio" element={
                <ErrorBoundary name="Reference Portfolio">
                  <ProtectedRoute>
                    <Suspense fallback={<PageLoader />}>
                      <ReferencePortfolio />
                    </Suspense>
                  </ProtectedRoute>
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
    </AuthProvider>
  </RootErrorBoundary>
);

export default App;
