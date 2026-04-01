import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Navbar from "./components/Navbar";
import LoadingCard from "./components/LoadingCard";
import useAuthStore from "./store/authStore";

const BotConsole = lazy(() => import("./pages/BotConsole"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const GlobalMarket = lazy(() => import("./pages/GlobalMarket"));
const HomePage = lazy(() => import("./pages/HomePage"));
const LedgerPage = lazy(() => import("./pages/LedgerPage"));
const ListingDetail = lazy(() => import("./pages/ListingDetail"));
const Login = lazy(() => import("./pages/Login"));
const Market = lazy(() => import("./pages/Market"));
const Verify = lazy(() => import("./pages/Verify"));

function ProtectedRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <div className="app-shell">
        <Navbar />
        <main id="main-content">
          <Suspense fallback={<LoadingCard message="Loading page…" />}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/market" element={<Market />} />
              <Route path="/global" element={<GlobalMarket />} />
              <Route path="/ledger" element={<LedgerPage />} />
              <Route path="/listing/:id" element={<ListingDetail />} />
              <Route path="/verify/:id" element={<Verify />} />
              <Route path="/bot" element={<BotConsole />} />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="/login" element={<Login />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
      <Toaster position="top-right" toastOptions={{ duration: 3800 }} />
    </BrowserRouter>
  );
}
