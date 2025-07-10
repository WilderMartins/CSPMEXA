import React from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const error = queryParams.get('error');

  const googleLoginUrl = '/api/v1/auth/google/login';

  return (
    <div className="login-page-placeholder">
      <h2>{t('loginPage.title')}</h2>
      {error && (
        <p style={{ color: 'red' }}>
          {t('loginPage.errorMessage', { error: decodeURIComponent(error) })}
        </p>
      )}
      <p>{t('loginPage.greeting')}</p>
      <a href={googleLoginUrl}>
        {t('loginPage.button')}
      </a>
      <p style={{marginTop: "20px", fontSize: "0.9em", color: "#555"}}>
        {t('loginPage.redirectMessage')}
      </p>
    </div>
  );
};

export default LoginPage;
