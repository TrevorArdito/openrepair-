import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "../components/Layout";
import AccountPage from "../features/account/AccountPage";
import CodeDetailPage from "../features/codes/CodeDetailPage";
import CodesPage from "../features/codes/CodesPage";
import EntryEditPage from "../features/entries/EntryEditPage";
import EntryPage from "../features/entries/EntryPage";
import HistoryPage from "../features/entries/HistoryPage";
import ModPage from "../features/entries/ModPage";
import { LoginPage, RegisterPage } from "../features/account/LoginPage";
import { ForgotPasswordPage, ResetPasswordPage, VerifyEmailPage } from "../features/account/PasswordPages";
import GaragePage from "../features/garage/GaragePage";
import AboutPage from "../features/info/AboutPage";
import NotFoundPage from "../features/info/NotFoundPage";
import SearchPage from "../features/search/SearchPage";
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
              <Route path="codes" element={<CodesPage />} />
              <Route path="codes/:code" element={<CodeDetailPage />} />
              <Route path="search" element={<SearchPage />} />
              <Route path="entries/new" element={<EntryEditPage />} />
              <Route path="entries/:id" element={<EntryPage />} />
              <Route path="entries/:id/edit" element={<EntryEditPage />} />
              <Route path="entries/:id/history" element={<HistoryPage />} />
              <Route path="mod" element={<ModPage />} />
              <Route path="account" element={<AccountPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="forgot-password" element={<ForgotPasswordPage />} />
              <Route path="reset-password" element={<ResetPasswordPage />} />
              <Route path="verify-email" element={<VerifyEmailPage />} />
              <Route path="about" element={<AboutPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </PrefsProvider>
  );
}
