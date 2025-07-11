import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext'; // Importar useAuth

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const auth = useAuth(); // Usar o contexto de autenticação
  // const navigate = useNavigate(); // Não é mais necessário para redirecionar após login aqui

  const queryParams = new URLSearchParams(location.search);
  const error = queryParams.get('error');

  const handleLogin = () => {
    auth.login(); // Chama a função de login do contexto
  };

  return (
    <div className="login-page-placeholder">
      <h2>{t('loginPage.title')}</h2>
      {error && (
        <p style={{ color: 'red' }}>
          {t('loginPage.errorMessage', { error: decodeURIComponent(error) })}
        </p>
      )}
      <p>{t('loginPage.greeting')}</p>
      <button onClick={handleLogin}> {/* Mudar de <a> para <button> */}
        {t('loginPage.button')}
      </button>
      <p style={{marginTop: "20px", fontSize: "0.9em", color: "#555"}}>
        {t('loginPage.redirectMessage')}
      </p>
    </div>
  );
};

export default LoginPage;
