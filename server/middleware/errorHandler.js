const winston = require('winston');
const path = require('path');

// Configure error logger
const errorLogger = winston.createLogger({
    level: 'error',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    transports: [
 feat/auth-error-handling-5447018483623698560
        new winston.transports.File({

        new winston.transports.File({ 
 main
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

// Operational error class
class AppError extends Error {
    constructor(message, statusCode) {
        super(message);
        this.statusCode = statusCode;
        this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
        this.isOperational = true;
 feat/auth-error-handling-5447018483623698560


        
 main
        Error.captureStackTrace(this, this.constructor);
    }
}

// MongoDB Cast error handler
const handleCastErrorDB = err => {
    const message = `Invalid ${err.path}: ${err.value}`;
    return new AppError(message, 400);
};

// MongoDB Duplicate fields error handler
const handleDuplicateFieldsDB = err => {
    const field = Object.keys(err.keyValue)[0];
    const value = err.keyValue[field];
    const message = `Duplicate field value: ${field} = '${value}'. Please use another value!`;
    return new AppError(message, 400);
};

// MongoDB Validation error handler
const handleValidationErrorDB = err => {
    const errors = Object.values(err.errors).map(el => el.message);
    const message = `Invalid input data. ${errors.join('. ')}`;
    return new AppError(message, 400);
};

// JWT error handler
const handleJWTError = () =>
    new AppError('Invalid token. Please log in again!', 401);

// JWT expired error handler
const handleJWTExpiredError = () =>
    new AppError('Your token has expired! Please log in again.', 401);

// Stripe error handler
const handleStripeError = err => {
    let message = 'Payment processing error';
    let statusCode = 400;
 feat/auth-error-handling-5447018483623698560


    
 main
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
 feat/auth-error-handling-5447018483623698560


    
 main
    return new AppError(message, statusCode);
};

// Send error in development
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
 feat/auth-error-handling-5447018483623698560

    // JSON response for non-API errors

    
    // Rendered website error
 main
    console.error('ERROR 💥', err);
    return res.status(err.statusCode).json({
        status: err.status,
        message: err.message,
        error: err,
        stack: err.stack
    });
};

// Send error in production
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
 feat/auth-error-handling-5447018483623698560


        
 main
        // Programming or other unknown error: don't leak error details
        errorLogger.error('ERROR 💥', {
            message: err.message,
            stack: err.stack,
            url: req.originalUrl,
            method: req.method
        });
 feat/auth-error-handling-5447018483623698560


        
 main
        return res.status(500).json({
            status: 'error',
            message: 'Something went very wrong!'
        });
    }
 feat/auth-error-handling-5447018483623698560

    // JSON response for non-API errors

    
    // Rendered website error
 main
    if (err.isOperational) {
        return res.status(err.statusCode).json({
            status: err.status,
            message: err.message
        });
    }
 feat/auth-error-handling-5447018483623698560


    
 main
    // Programming or other unknown error: don't leak error details
    errorLogger.error('ERROR 💥', {
        message: err.message,
        stack: err.stack,
        url: req.originalUrl,
        method: req.method
    });
 feat/auth-error-handling-5447018483623698560


    
 main
    return res.status(500).json({
        status: 'error',
        message: 'Please try again later.'
    });
};

// Global error handling middleware
 feat/auth-error-handling-5447018483623698560
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

const globalErrorHandler = (err, req, res, next) => {
    err.statusCode = err.statusCode || 500;
    err.status = err.status || 'error';
    
    if (process.env.NODE_ENV === 'development') {
        sendErrorDev(err, req, res);
    } else if (process.env.NODE_ENV === 'production') {
        let error = Object.assign(err);
        error.message = err.message;
        
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
 main
    }
};

// Not found middleware
 feat/auth-error-handling-5447018483623698560
exports.notFound = (req, res, next) => {

const notFound = (req, res, next) => {
 main
    const err = new AppError(`Can't find ${req.originalUrl} on this server!`, 404);
    next(err);
};

// Async error wrapper
 feat/auth-error-handling-5447018483623698560
exports.catchAsync = fn => {

const catchAsync = fn => {
 main
    return (req, res, next) => {
        fn(req, res, next).catch(next);
    };
};

 feat/auth-error-handling-5447018483623698560
exports.AppError = AppError;
exports.errorLogger = errorLogger;

module.exports = {
    AppError,
    globalErrorHandler,
    notFound,
    catchAsync,
    errorLogger
};
 main
