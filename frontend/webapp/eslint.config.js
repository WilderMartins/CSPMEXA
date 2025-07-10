import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import pluginReactConfig from "eslint-plugin-react/configs/recommended.js";
import eslintPluginReactHooks from "eslint-plugin-react-hooks";
import eslintPluginReactRefresh from "eslint-plugin-react-refresh";

export default [
  { files: ["**/*.{js,mjs,cjs,ts,jsx,tsx}"] },
  { languageOptions: { globals: globals.browser } },
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,
  { // Configurações específicas para React
    files: ["src/**/*.{ts,tsx}"],
    ...pluginReactConfig,
    settings: {
      react: {
        version: "detect" // Detecta automaticamente a versão do React
      }
    },
    plugins: {
      ...pluginReactConfig.plugins, // Mantém os plugins originais do pluginReactConfig
      "react-hooks": eslintPluginReactHooks,
      "react-refresh": eslintPluginReactRefresh,
    },
    rules: {
      ...pluginReactConfig.rules,
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "react/react-in-jsx-scope": "off", // Não necessário com o novo JSX transform
      "react/prop-types": "off" // Desabilitar se usando TypeScript para props
    }
  }
];
