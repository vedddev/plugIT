import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RequestsPage } from "./pages/RequestsPage";
import { ProvidersPage } from "./pages/ProvidersPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ApiKeysPage } from "./pages/ApiKeysPage";
import { UsagePage } from "./pages/UsagePage";
import { SettingsPage } from "./pages/SettingsPage";
import { AppLayout } from "./layouts/AppLayout";
import { useAuth } from "./services/AuthContext";
import { ToastProvider } from "./services/toast";
import { Spinner } from "./components/Spinner";

function ProtectedRoutes() {
  const { user, ready } = useAuth();
  if (!ready) {
    return (
      <div className="full-center">
        <Spinner size={20} />
      </div>
    );
  }
  if (!user) {
    return <LoginPage />;
  }
  return (
    <AppLayout key={user.id}>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/requests" element={<RequestsPage />} />
        <Route path="/providers" element={<ProvidersPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="/usage" element={<UsagePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </AppLayout>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<LoginPage registerMode />} />
        <Route path="/*" element={<ProtectedRoutes />} />
      </Routes>
    </ToastProvider>
  );
}
