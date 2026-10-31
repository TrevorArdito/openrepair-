import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import AccountPage from "../features/account/AccountPage";
import { LoginPage, RegisterPage } from "../features/account/LoginPage";
import GaragePage from "../features/garage/GaragePage";
import AboutPage from "../features/info/AboutPage";
import ComingSoonPage from "../features/info/ComingSoonPage";
import NotFoundPage from "../features/info/NotFoundPage";
import HomePage from "../features/vehicles/HomePage";
import VehiclePage from "../features/vehicles/VehiclePage";
import { AuthProvider } from "../lib/auth";
import { PrefsProvider } from "../lib/prefs";

export default function App() {
  return (
    <PrefsProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="vehicle/:id" element={<VehiclePage />} />
              <Route path="garage" element={<GaragePage />} />
              <Route path="codes" element={<ComingSoonPage titleKey="nav.codes" />} />
              <Route path="search" element={<ComingSoonPage titleKey="nav.search" />} />
              <Route path="account" element={<AccountPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="about" element={<AboutPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </PrefsProvider>
  );
}
