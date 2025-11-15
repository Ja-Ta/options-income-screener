/**
 * API routes for picks endpoints
 */

import express from 'express';
import db from '../db.js';

const router = express.Router();

/**
 * GET /api/picks
 * Get filtered picks with optional query parameters
 */
router.get('/', (req, res) => {
  try {
    const {
      date,
      strategy,
      minScore = 0,
      minIVR = 0,
      minROI = 0,
      sentimentSignal,  // NEW: Filter by contrarian signal (long/short/none)
      limit = 100,
      offset = 0
    } = req.query;

    const filters = {
      date,
      strategy,
      minScore: parseFloat(minScore),
      minIVR: parseFloat(minIVR),
      minROI: parseFloat(minROI),
      sentimentSignal,  // NEW: Add sentiment filter
      limit: parseInt(limit),
      offset: parseInt(offset)
    };

    const picks = db.getFilteredPicks(filters);

    res.json({
      success: true,
      count: picks.length,
      picks
    });
  } catch (error) {
    console.error('Error fetching picks:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/picks/latest
 * Get picks from the most recent date with optional filters
 */
router.get('/latest', (req, res) => {
  try {
    const latestDate = db.getLatestDate();

    if (!latestDate) {
      return res.json({
        success: true,
        message: 'No picks available',
        picks: []
      });
    }

    // Apply filters if provided
    const {
      strategy,
      minScore = 0,
      minIVR = 0,
      minROI = 0,
      sentimentSignal,
      limit = 100,
      offset = 0
    } = req.query;

    const filters = {
      date: latestDate,
      strategy,
      minScore: parseFloat(minScore),
      minIVR: parseFloat(minIVR),
      minROI: parseFloat(minROI),
      sentimentSignal,
      limit: parseInt(limit),
      offset: parseInt(offset)
    };

    const picks = db.getFilteredPicks(filters);

    res.json({
      success: true,
      date: latestDate,
      count: picks.length,
      picks
    });
  } catch (error) {
    console.error('Error fetching latest picks:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/picks/top
 * Get top picks across all dates
 */
router.get('/top', (req, res) => {
  try {
    const { limit = 10 } = req.query;
    const picks = db.getTopPicks(parseInt(limit));

    res.json({
      success: true,
      count: picks.length,
      picks
    });
  } catch (error) {
    console.error('Error fetching top picks:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/picks/date/:date
 * Get all picks for a specific date
 */
router.get('/date/:date', (req, res) => {
  try {
    const { date } = req.params;
    const picks = db.getPicksByDate(date);

    res.json({
      success: true,
      date,
      count: picks.length,
      picks
    });
  } catch (error) {
    console.error('Error fetching picks by date:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/picks/:id
 * Get a single pick by ID with rationale
 */
router.get('/:id', (req, res) => {
  try {
    const { id } = req.params;
    const pick = db.getPickById(parseInt(id));

    if (!pick) {
      return res.status(404).json({
        success: false,
        error: 'Pick not found'
      });
    }

    res.json({
      success: true,
      pick
    });
  } catch (error) {
    console.error('Error fetching pick:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

export default router;