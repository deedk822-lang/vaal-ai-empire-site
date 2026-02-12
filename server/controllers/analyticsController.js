const { catchAsync } = require('../middleware/errorHandler');
const { logger, sanitizeObject } = require('../utils/secureLogger');

exports.logDocumentDownload = catchAsync(async (req, res, next) => {
  // Use secure logger to prevent log injection
  logger.info('Document downloaded', sanitizeObject({
    userId: req.user?._id,
    documentId: req.body.documentId,
    timestamp: new Date().toISOString(),
    ip: req.ip,
  }));
  
  res.status(200).json({ status: 'success' });
});
