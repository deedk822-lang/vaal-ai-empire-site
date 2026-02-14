const { catchAsync } = require('../middleware/errorHandler');

exports.logDocumentDownload = catchAsync(async (req, res, next) => {
    // In a real application, you would log this to a database or analytics service
    console.log('Document downloaded:', req.body);
    res.status(200).json({ status: 'success' });
});
