module.exports = {
  testEnvironment: 'jsdom',
  transform: {
    '^.+\\.(ts|tsx|js|jsx)$': 'babel-jest',
  },
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    'react-markdown': '<rootDir>/node_modules/react-markdown/react-markdown.js',
  },
  transformIgnorePatterns: [
    "/node_modules/(?!axios)/"
  ],
};
