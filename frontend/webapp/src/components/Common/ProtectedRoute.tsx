import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

type UserRole = 'User' | 'TechnicalLead' | 'Manager' | 'Administrator' | 'SuperAdministrator';

interface ProtectedRouteProps {
  children: JSX.Element;
  requiredRole: UserRole;
}

const ROLES_HIERARCHY: Record<UserRole, number> = {
  'User': 1,
  'TechnicalLead': 2,
  'Manager': 3,
  'Administrator': 4,
  'SuperAdministrator': 5,
};

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    // Se não estiver autenticado, o roteador principal já redireciona para /login
    // mas adicionamos aqui como uma salvaguarda.
    return <Navigate to="/" replace />;
  }

  const userLevel = user?.role ? ROLES_HIERARCHY[user.role as UserRole] || 0 : 0;
  const requiredLevel = ROLES_HIERARCHY[requiredRole];

  if (userLevel >= requiredLevel) {
    return children;
  } else {
    return <Navigate to="/access-denied" replace />;
  }
};

export default ProtectedRoute;
