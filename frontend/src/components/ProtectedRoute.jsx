import { Navigate } from 'react-router-dom';
import api from '../api/client';

export default function ProtectedRoute({ children }) {
  const token = api.getToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}