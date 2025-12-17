// server/agents/auth-validator.js
const User = require('../models/User');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const colors = require('colors');

const tests = {
    'JWT Secret configured': () => {
        const secret = process.env.JWT_SECRET;
        if (!secret) {
            return {
                passed: false,
                message: 'JWT_SECRET is not set in the environment. This is a critical security risk.',
                fix: 'Generate a secure secret and add it to your .env file. Example: JWT_SECRET=your-very-long-and-secure-secret'
            };
        }
        if (secret.length < 32) {
            return {
                passed: false,
                message: `JWT_SECRET is too short (${secret.length} chars). It must be at least 32 characters for security.`,
                fix: 'Generate a longer, more secure secret. Use a password manager or a command like `openssl rand -base64 32`.'
            };
        }
        return { passed: true };
    },
    'JWT token generation & validation working': () => {
        try {
            const secret = process.env.JWT_SECRET || 'default-secret-for-testing';
            const token = jwt.sign({ id: 'test' }, secret, { expiresIn: '1m' });
            const decoded = jwt.verify(token, secret);
            if (decoded.id !== 'test') {
                throw new Error('Decoded ID does not match.');
            }
            return { passed: true };
        } catch (err) {
            return {
                passed: false,
                message: `JWT functionality failed: ${err.message}`,
                fix: 'Ensure the JWT library is installed correctly (`npm install jsonwebtoken`) and that the secret is valid.'
            };
        }
    },
    'Password hashing & verification working': async () => {
        try {
            const password = 'password123';
            const hash = await bcrypt.hash(password, 12);
            const isMatch = await bcrypt.compare(password, hash);
            if (!isMatch) {
                throw new Error('Password verification failed.');
            }
            return { passed: true };
        } catch (err) {
            return {
                passed: false,
                message: `Bcrypt functionality failed: ${err.message}`,
                fix: 'Ensure the bcryptjs library is installed correctly (`npm install bcryptjs`).'
            };
        }
    },
    'User model validation working': async () => {
        const user = new User();
        try {
            await user.validate();
            return {
                passed: false,
                message: 'User model validation did not trigger for an empty user. Required fields are likely missing validation.',
                fix: 'Check the User model schema and ensure fields like `email`, `password`, `firstName`, and `lastName` have `required: true` validators.'
            };
        } catch (err) {
            if (err.name === 'ValidationError') {
                return { passed: true };
            }
            return {
                passed: false,
                message: `User model validation threw an unexpected error: ${err.message}`,
                fix: 'Review the User model for schema errors.'
            };
        }
    },
    'Account locking mechanism configured': () => {
        if (User.schema.methods.incrementLoginAttempts && User.schema.virtuals.isLocked) {
            return { passed: true, message: 'Account locking methods are present on the User model.' };
        }
        return {
            passed: false,
            message: 'Account locking mechanism is not fully implemented on the User model.',
            fix: 'Ensure the `incrementLoginAttempts` method and `isLocked` virtual are defined in `server/models/User.js`.'
        };
    }
};

const run = async () => {
    console.log(colors.cyan('\n┌──────────────────────────────────────────────┐'));
    console.log(colors.cyan('│ 1/2 Authentication Validator                 │'));
    console.log(colors.cyan('└──────────────────────────────────────────────┘\n'));

    const results = {
        passed: 0,
        failed: 0,
        warnings: 0,
        errors: []
    };

    for (const [name, test] of Object.entries(tests)) {
        console.log(colors.yellow(`[${new Date().toISOString()}] AUTH-VALIDATOR: Testing ${name}...`));
        const result = await test();
        if (result.passed) {
            console.log(colors.green(`✅ ${name}`));
            results.passed++;
        } else {
            console.log(colors.red(`❌ ${name}: ${result.message}`));
            results.failed++;
            results.errors.push({ test: name, ...result });
        }
    }

    console.log(colors.bold('\n📊 AUTHENTICATION VALIDATION SUMMARY'));
    console.log(colors.green(`✅ Passed: ${results.passed}`));
    console.log(colors.red(`❌ Failed: ${results.failed}`));

    if (results.failed > 0) {
        console.log(colors.red.bold('\n📚 AUTHENTICATION TROUBLESHOOTING COOKBOOK'));
        console.log(colors.red('══════════════════════════════════════════\n'));
        results.errors.forEach((error, i) => {
            console.log(colors.red.bold(`${i + 1}. ❌ ${error.test}`));
            console.log(`   ${colors.white(error.message)}\n`);
            console.log(colors.yellow.bold('   FIX:'));
            console.log(`   ${colors.cyan(error.fix)}\n`);
        });
    }

    return results;
};

module.exports = { run };
