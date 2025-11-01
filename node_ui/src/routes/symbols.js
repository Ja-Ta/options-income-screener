/**
 * API routes for symbol-related endpoints
 */

import express from 'express';
import db from '../db.js';

const router = express.Router();

/**
 * GET /api/symbols/search
 * Search for picks by symbol pattern
 */
router.get('/search', (req, res) => {
  try {
    const { q } = req.query;

    if (!q || q.length < 1) {
      return res.status(400).json({
        success: false,
        error: 'Search query required (min 1 character)'
      });
    }

    const picks = db.searchBySymbol(q.toUpperCase());

    res.json({
      success: true,
      query: q,
      count: picks.length,
      picks
    });
  } catch (error) {
    console.error('Error searching symbols:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * GET /api/symbols/:symbol/history
 * Get historical picks for a specific symbol
 */
router.get('/:symbol/history', (req, res) => {
  try {
    const { symbol } = req.params;
    const history = db.getSymbolHistory(symbol.toUpperCase());

    res.json({
      success: true,
      symbol: symbol.toUpperCase(),
      count: history.length,
      history
    });
  } catch (error) {
    console.error('Error fetching symbol history:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

export default router;