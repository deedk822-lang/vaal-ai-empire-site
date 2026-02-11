module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true,
    jest: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:node/recommended',
    'plugin:prettier/recommended',
  ],
  plugins: ['node', 'prettier'],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
  },
  rules: {
    // Prettier
    'prettier/prettier': 'error',
    
    // Node.js best practices
    'node/no-unpublished-require': 'off',
    'node/no-missing-require': 'error',
    'node/no-extraneous-require': 'warn',
    
    // Allow process.exit in server files
    'no-process-exit': 'off',
    
    // Relax async/await rules
    'require-await': 'off',
    'no-return-await': 'off',
    
    // General best practices
    'no-console': 'off',
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    'no-undef': 'error',
    'no-var': 'error',
    'prefer-const': 'error',
    'prefer-arrow-callback': 'error',
    'eqeqeq': ['error', 'always'],
    'curly': ['error', 'all'],
    'no-throw-literal': 'error',
    
    // Code quality - relaxed for this project
    'complexity': ['warn', 15],
    'max-lines-per-function': ['warn', 100],
    'max-params': ['warn', 6],
    'no-case-declarations': 'off',
  },
  overrides: [
    {
      files: ['server/**/*.js'],
      env: {
        node: true,
      },
      rules: {
        'no-console': 'off',
        'node/no-process-exit': 'off',
      },
    },
    {
      files: ['js/**/*.js'],
      env: {
        browser: true,
      },
      rules: {
        'node/no-unsupported-features/node-builtins': 'off',
      },
    },
    {
      files: ['**/*.test.js', '**/*.spec.js'],
      env: {
        jest: true,
      },
      rules: {
        'no-unused-vars': 'off',
      },
    },
  ],
  ignorePatterns: [
    'node_modules/',
    'server/node_modules/',
    'dist/',
    'build/',
    'coverage/',
    '*.min.js',
    'public/',
  ],
};
