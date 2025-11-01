/**
 * API routes for statistics endpoints
 */

import express from 'express';
import db from '../db.js';

const router = express.Router();

/**
 * GET /api/stats
 * Get overall statistics
 */
router.get('/', (req, res) => {
  try {
    const stats = db.getStats();

    res.json({
      success: true,
      stats
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/stats/daily/:date
 * Get daily summary statistics
 */
router.get('/daily/:date', (req, res) => {
  try {
    const { date } = req.params;
    const summary = db.getDailySummary(date);

    res.json({
      success: true,
      summary
    });
  } catch (error) {
    console.error('Error fetching daily summary:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/stats/history
 * Get historical performance data
 */
router.get('/history', (req, res) => {
  try {
    const { days = 30 } = req.query;
    const history = db.getHistoricalData(parseInt(days));

    res.json({
      success: true,
      days: parseInt(days),
      history
    });
  } catch (error) {
    console.error('Error fetching history:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/stats/dates
 * Get all available dates with picks
 */
router.get('/dates', (req, res) => {
  try {
    const dates = db.getAvailableDates();

    res.json({
      success: true,
      count: dates.length,
      dates
    });
  } catch (error) {
    console.error('Error fetching dates:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/stats/latest-date
 * Get the latest date with picks
 */
router.get('/latest-date', (req, res) => {
  try {
    const latestDate = db.getLatestDate();

    res.json({
      success: true,
      date: latestDate
    });
  } catch (error) {
    console.error('Error fetching latest date:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

export default router;