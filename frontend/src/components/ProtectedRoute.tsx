import { Navigate } from 'react-router-dom';
import api from '../api/client';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return api.getToken() ? <>{children}</> : <Navigate to="/login" replace />;
}