const express = require('express');
const { logDocumentDownload } = require('../controllers/analyticsController');
const { protect } = require('../middleware/auth');

const router = express.Router();

router.post('/document-download', logDocumentDownload);

module.exports = router;
