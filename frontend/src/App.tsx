import { AuthProvider } from './core/auth/AuthContext';
import { AppRouter } from './core/router';

export function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
