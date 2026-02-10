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
    'plugin:security/recommended',
    'plugin:prettier/recommended',
  ],
  plugins: ['node', 'security', 'prettier'],
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
    
    // Security
    'security/detect-object-injection': 'warn',
    'security/detect-non-literal-regexp': 'warn',
    'security/detect-unsafe-regex': 'error',
    'security/detect-buffer-noassert': 'error',
    'security/detect-eval-with-expression': 'error',
    'security/detect-no-csrf-before-method-override': 'error',
    'security/detect-non-literal-fs-filename': 'warn',
    'security/detect-non-literal-require': 'warn',
    'security/detect-possible-timing-attacks': 'warn',
    'security/detect-pseudoRandomBytes': 'error',
    
    // General best practices
    'no-console': 'off', // Allow console in this project
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'no-undef': 'error',
    'no-var': 'error',
    'prefer-const': 'error',
    'prefer-arrow-callback': 'error',
    'eqeqeq': ['error', 'always'],
    'curly': ['error', 'all'],
    'no-throw-literal': 'error',
    'no-return-await': 'error',
    'require-await': 'error',
    
    // Code quality
    'complexity': ['warn', 10],
    'max-lines-per-function': ['warn', 50],
    'max-params': ['warn', 4],
  },
  overrides: [
    {
      files: ['server/**/*.js'],
      env: {
        node: true,
      },
      rules: {
        'no-console': 'off',
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
