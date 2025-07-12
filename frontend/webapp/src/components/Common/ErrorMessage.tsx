import React from 'react';
import { Alert as MantineAlert, Text } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

interface ErrorMessageProps {
  title?: string;
  message: string | null;
  onClose?: () => void;
  showCloseButton?: boolean;
}

const ErrorMessage: React.FC<ErrorMessageProps> = ({
  title,
  message,
  onClose,
  showCloseButton = true,
}) => {
  const { t } = useTranslation();

  if (!message) {
    return null;
  }

  const displayTitle = title || t('common.errorTitle', 'An Error Occurred');

  return (
    <MantineAlert
      icon={<IconAlertCircle size="1rem" />}
      title={displayTitle}
      color="red"
      withCloseButton={showCloseButton && !!onClose} // Mostrar botão de fechar apenas se onClose for fornecido
      onClose={onClose}
      mt="md"
      radius="md"
      variant="filled" // Para um visual mais destacado
    >
      <Text>{message}</Text>
    </MantineAlert>
  );
};

export default ErrorMessage;
