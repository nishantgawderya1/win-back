import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";

import AppLayout from "./layouts/AppLayout.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import OnboardingLayout from "./layouts/OnboardingLayout.jsx";

import Landing from "./pages/Landing.jsx";
import Auth from "./pages/Auth.jsx";
import Connect from "./pages/onboarding/Connect.jsx";
import Mode from "./pages/onboarding/Mode.jsx";
import Done from "./pages/onboarding/Done.jsx";

import Dashboard from "./pages/app/Dashboard.jsx";
import BatchUpload from "./pages/app/BatchUpload.jsx";
import BatchResults from "./pages/app/BatchResults.jsx";
import Feed from "./pages/app/Feed.jsx";
import Audit from "./pages/app/Audit.jsx";
import Halted from "./pages/app/Halted.jsx";
import Exceptions from "./pages/app/Exceptions.jsx";
import Settings from "./pages/app/Settings.jsx";

/** Signed in, and through onboarding, before any product screen renders. */
function RequireAuth({ children }) {
  const { isAuthed, isOnboarded } = useAuth();
  if (!isAuthed) return <Navigate to="/auth" replace />;
  if (!isOnboarded) return <Navigate to="/onboarding/connect" replace />;
  return children;
}

/** Onboarding itself needs a session but not a completed onboarding. */
function RequireSession({ children }) {
  const { isAuthed } = useAuth();
  return isAuthed ? children : <Navigate to="/auth" replace />;
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />

      <Route element={<AuthLayout />}>
        <Route path="/auth" element={<Auth />} />
      </Route>

      <Route
        element={
          <RequireSession>
            <OnboardingLayout />
          </RequireSession>
        }
      >
        <Route path="/onboarding/connect" element={<Connect />} />
        <Route path="/onboarding/mode" element={<Mode />} />
        <Route path="/onboarding/done" element={<Done />} />
      </Route>

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/batch" element={<BatchUpload />} />
        <Route path="/batch/:id" element={<BatchResults />} />
        <Route path="/feed" element={<Feed />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/halted" element={<Halted />} />
        <Route path="/exceptions" element={<Exceptions />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
