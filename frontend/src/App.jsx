import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api";
import AdminPage from "./pages/AdminPage";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";

function Protected({ children }) {
  if (!getToken()) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AuthPage />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <DashboardPage />
          </Protected>
        }
      />
      <Route
        path="/admin"
        element={
          <Protected>
            <AdminPage />
          </Protected>
        }
      />
    </Routes>
  );
}
