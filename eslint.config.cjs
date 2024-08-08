const { FlatCompat } = require('@eslint/eslintrc');
const tsParser = require('@typescript-eslint/parser');
const tsPlugin = require('@typescript-eslint/eslint-plugin');
const importPlugin = require('eslint-plugin-import');

const compat = new FlatCompat();

module.exports = [
  {
    files: ['src/**/*.{js,ts}'],
    languageOptions: {
      parser: tsParser,
      sourceType: 'module',
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      import: importPlugin,
    },
    rules: {
      'max-len': ['error', { code: 80 }],
      'indent': ['error', 2],
      'no-tabs': 'error',
      'linebreak-style': ['error', 'unix'],
      'quotes': ['error', 'single'],
      'semi': ['error', 'always'],
      '@typescript-eslint/no-explicit-any': 'off',
      'import/no-named-as-default': 'off', 
      'import/no-named-as-default-member': 'off', 
    },
  },
];