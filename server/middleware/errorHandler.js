/**
 * Error Handling Middleware Module
 * 
 * Provides centralized error handling for the Vaal AI Empire platform.
 * Handles operational errors, database errors, JWT errors, and payment errors.
 * 
 * @module server/middleware/errorHandler
 * @requires winston
 * @requires path
 * 
 * @security APEX v2.0 Compliant
 * @security Sanitized error messages in production
 * @security No stack traces exposed to clients in production
 * @security Structured logging for audit trail
 */

const winston = require('winston');
const path = require('path');

/**
 * Winston logger for error logging.
 * Logs to file and console with rotation.
 * 
 * @type {winston.Logger}
 * @constant
 */
const errorLogger = winston.createLogger({
    level: 'error',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({
            filename: path.join(__dirname, '../logs/error.log'),
            maxsize: 5242880, // 5MB
            maxFiles: 5
        }),
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.simple()
            )
        })
    ]
});

/**
 * Custom error class for operational errors.
 * Operational errors are expected errors that can be handled gracefully.
 * 
 * @class AppError
 * @extends Error
 * 
 * @param {string} message - Error message to display
 * @param {number} statusCode - HTTP status code
 * 
 * @property {number} statusCode - HTTP status code
 * @property {string} status - 'fail' for 4xx, 'error' for 5xx
 * @property {boolean} isOperational - Always true for AppError instances
 * 
 * @example
 * throw new AppError('User not found', 404);
 * throw new AppError('Invalid credentials', 401);
 */
class AppError extends Error {
    constructor(message, statusCode) {
        super(message);
        this.statusCode = statusCode;
        this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
        this.isOperational = true;
        Error.captureStackTrace(this, this.constructor);
    }
}

/**
 * Handles MongoDB CastError (invalid ObjectId).
 * 
 * @function handleCastErrorDB
 * @param {Error} err - MongoDB CastError
 * @returns {AppError} Operational error with user-friendly message
 * @private
 */
const handleCastErrorDB = err => {
    const message = `Invalid ${err.path}: ${err.value}`;
    return new AppError(message, 400);
};

/**
 * Handles MongoDB duplicate key error (code 11000).
 * 
 * @function handleDuplicateFieldsDB
 * @param {Error} err - MongoDB duplicate key error
 * @returns {AppError} Operational error with user-friendly message
 * @private
 */
const handleDuplicateFieldsDB = err => {
    const field = Object.keys(err.keyValue)[0];
    const value = err.keyValue[field];
    const message = `Duplicate field value: ${field} = '${value}'. Please use another value!`;
    return new AppError(message, 400);
};

/**
 * Handles MongoDB validation errors.
 * 
 * @function handleValidationErrorDB
 * @param {Error} err - MongoDB ValidationError
 * @returns {AppError} Operational error with all validation messages
 * @private
 */
const handleValidationErrorDB = err => {
    const errors = Object.values(err.errors).map(el => el.message);
    const message = `Invalid input data. ${errors.join('. ')}`;
    return new AppError(message, 400);
};

/**
 * Handles JWT invalid token errors.
 * 
 * @function handleJWTError
 * @returns {AppError} Operational error for invalid token
 * @private
 */
const handleJWTError = () =>
    new AppError('Invalid token. Please log in again!', 401);

/**
 * Handles JWT expired token errors.
 * 
 * @function handleJWTExpiredError
 * @returns {AppError} Operational error for expired token
 * @private
 */
const handleJWTExpiredError = () =>
    new AppError('Your token has expired! Please log in again.', 401);

/**
 * Handles Stripe payment errors.
 * Maps Stripe error types to user-friendly messages.
 * 
 * @function handleStripeError
 * @param {Error} err - Stripe error
 * @returns {AppError} Operational error with appropriate status code
 * @private
 */
const handleStripeError = err => {
    let message = 'Payment processing error';
    let statusCode = 400;
    if (err.type === 'StripeCardError') {
        message = err.message || 'Your card was declined';
    } else if (err.type === 'StripeInvalidRequestError') {
        message = 'Invalid payment request. Please check your payment details.';
    } else if (err.type === 'StripeAPIError') {
        message = 'Payment gateway error. Please try again later.';
        statusCode = 503;
    } else if (err.type === 'StripeConnectionError') {
        message = 'Network error. Please check your connection.';
        statusCode = 503;
    } else if (err.type === 'StripeAuthenticationError') {
        message = 'Payment authentication failed';
        statusCode = 500;
    } else if (err.type === 'StripeRateLimitError') {
        message = 'Too many requests. Please try again later.';
        statusCode = 429;
    }
    return new AppError(message, statusCode);
};

/**
 * Sends detailed error response in development environment.
 * Includes full error details and stack trace for debugging.
 * 
 * @function sendErrorDev
 * @param {Error} err - Error object
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @returns {void} Sends JSON error response
 * @private
 */
const sendErrorDev = (err, req, res) => {
    // API error
    if (req.originalUrl.startsWith('/api')) {
        return res.status(err.statusCode).json({
            status: err.status,
            error: err,
            message: err.message,
            stack: err.stack
        });
    }
    // JSON response for non-API errors
    console.error('ERROR 💥', err);
    return res.status(err.statusCode).json({
        status: err.status,
        message: err.message,
        error: err,
        stack: err.stack
    });
};

/**
 * Sends sanitized error response in production environment.
 * Only exposes details for operational errors, hides internal errors.
 * 
 * @function sendErrorProd
 * @param {Error} err - Error object
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @returns {void} Sends JSON error response
 * @private
 * 
 * @security Never exposes stack traces to clients
 * @security Logs internal errors for investigation
 */
const sendErrorProd = (err, req, res) => {
    // API error
    if (req.originalUrl.startsWith('/api')) {
        // Operational, trusted error: send message to client
        if (err.isOperational) {
            return res.status(err.statusCode).json({
                status: err.status,
                message: err.message
            });
        }
        // Programming or other unknown error: don't leak error details
        errorLogger.error('ERROR 💥', {
            message: err.message,
            stack: err.stack,
            url: req.originalUrl,
            method: req.method
        });
        return res.status(500).json({
            status: 'error',
            message: 'Something went very wrong!'
        });
    }
    // JSON response for non-API errors
    if (err.isOperational) {
        return res.status(err.statusCode).json({
            status: err.status,
            message: err.message
        });
    }
    // Programming or other unknown error: don't leak error details
    errorLogger.error('ERROR 💥', {
        message: err.message,
        stack: err.stack,
        url: req.originalUrl,
        method: req.method
    });
    return res.status(500).json({
        status: 'error',
        message: 'Please try again later.'
    });
};

/**
 * Global error handling middleware.
 * Must be registered last in the Express middleware chain.
 * 
 * @function globalErrorHandler
 * @param {Error} err - Error object
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {void} Sends JSON error response
 * 
 * @example
 * // Register as the last middleware
 * app.use(globalErrorHandler);
 * 
 * @example
 * // Errors are automatically caught and formatted
 * app.get('/user/:id', (req, res, next) => {
 *   User.findById(req.params.id)
 *     .then(user => res.json(user))
 *     .catch(next); // Error handled by globalErrorHandler
 * });
 */
exports.globalErrorHandler = (err, req, res, next) => {
    err.statusCode = err.statusCode || 500;
    err.status = err.status || 'error';

    if (process.env.NODE_ENV === 'development') {
        sendErrorDev(err, req, res);
    } else if (process.env.NODE_ENV === 'production') {
        let error = err;

        // Mongoose bad ObjectId
        if (error.name === 'CastError') error = handleCastErrorDB(error);

        // Mongoose duplicate key
        if (error.code === 11000) error = handleDuplicateFieldsDB(error);

        // Mongoose validation error
        if (error.name === 'ValidationError') error = handleValidationErrorDB(error);

        // JWT errors
        if (error.name === 'JsonWebTokenError') error = handleJWTError();
        if (error.name === 'TokenExpiredError') error = handleJWTExpiredError();

        // Stripe errors
        if (error.type && error.type.startsWith('Stripe')) error = handleStripeError(error);

        sendErrorProd(error, req, res);
    } else {
        // Fallback for other environments
        sendErrorDev(err, req, res);
    }
};

/**
 * Not found middleware for handling 404 errors.
 * Creates an operational error for unknown routes.
 * 
 * @function notFound
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {void} Calls next with 404 AppError
 * 
 * @example
 * // Register after all routes
 * app.use(notFound);
 */
exports.notFound = (req, res, next) => {
    const err = new AppError(`Can't find ${req.originalUrl} on this server!`, 404);
    next(err);
};

/**
 * Async error wrapper for route handlers.
 * Catches errors in async functions and passes them to error middleware.
 * 
 * @function catchAsync
 * @param {Function} fn - Async route handler function
 * @returns {Function} Wrapped function that catches errors
 * 
 * @example
 * // Wrap async route handlers
 * exports.getUser = catchAsync(async (req, res, next) => {
 *   const user = await User.findById(req.params.id);
 *   if (!user) return next(new AppError('User not found', 404));
 *   res.json(user);
 * });
 */
exports.catchAsync = fn => {
    return (req, res, next) => {
        fn(req, res, next).catch(next);
    };
};

/**
 * @typedef {Object} ErrorHandlerModule
 * @property {Class} AppError - Custom operational error class
 * @property {Function} globalErrorHandler - Global error handling middleware
 * @property {Function} notFound - 404 not found middleware
 * @property {Function} catchAsync - Async error wrapper
 * @property {winston.Logger} errorLogger - Winston error logger
 */

exports.AppError = AppError;
exports.errorLogger = errorLogger;
