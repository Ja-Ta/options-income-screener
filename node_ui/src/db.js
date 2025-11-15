/**
 * Database helper module for SQLite operations
 * Read-only access to screening results
 */

import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Database path configuration
// Points to unified database at project root
const DB_PATH = process.env.DB_PATH || path.resolve(__dirname, '../../data/screener.db');

class DatabaseService {
  constructor() {
    this.db = null;
    this.connect();
  }

  connect() {
    try {
      this.db = new Database(DB_PATH, {
        readonly: false,  // Changed to allow monitoring route updates
        fileMustExist: false
      });
      console.log(`✅ Connected to database: ${DB_PATH}`);

      // Enable WAL mode for better concurrent access
      this.db.pragma('journal_mode = WAL');

    } catch (error) {
      console.error(`❌ Database connection failed: ${error.message}`);
      this.db = null;
    }
  }

  isConnected() {
    return this.db !== null;
  }

  /**
   * Get the latest date with picks
   */
  getLatestDate() {
    if (!this.db) throw new Error('Database not connected');

    const row = this.db.prepare('SELECT MAX(date) as latest FROM picks').get();
    return row?.latest || null;
  }

  /**
   * Get all picks for a specific date
   */
  getPicksByDate(date) {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT p.*,
             r.summary as rationale,
             e.earnings_date,
             CAST((julianday(e.earnings_date) - julianday('now')) AS INT) as earnings_days_until
      FROM picks p
      LEFT JOIN rationales r ON p.id = r.pick_id
        AND r.created_at = (
          SELECT MAX(created_at)
          FROM rationales
          WHERE pick_id = p.id
        )
      LEFT JOIN earnings e ON p.symbol = e.symbol
        AND e.earnings_date >= date('now')
        AND e.earnings_date = (
          SELECT MIN(earnings_date)
          FROM earnings
          WHERE symbol = p.symbol AND earnings_date >= date('now')
        )
      WHERE p.date = ?
      ORDER BY p.score DESC
    `).all(date);
  }

  /**
   * Get filtered picks with pagination
   */
  getFilteredPicks(filters = {}) {
    if (!this.db) throw new Error('Database not connected');

    const {
      date,
      strategy,
      minScore = 0,
      minIVR = 0,
      minROI = 0,
      sentimentSignal,  // NEW: Filter by contrarian signal
      limit = 100,
      offset = 0
    } = filters;

    let query = `
      SELECT p.*,
             r.summary as rationale,
             e.earnings_date,
             CAST((julianday(e.earnings_date) - julianday('now')) AS INT) as earnings_days_until
      FROM picks p
      LEFT JOIN rationales r ON p.id = r.pick_id
        AND r.created_at = (
          SELECT MAX(created_at)
          FROM rationales
          WHERE pick_id = p.id
        )
      LEFT JOIN earnings e ON p.symbol = e.symbol
        AND e.earnings_date >= date('now')
        AND e.earnings_date = (
          SELECT MIN(earnings_date)
          FROM earnings
          WHERE symbol = p.symbol AND earnings_date >= date('now')
        )
      WHERE 1=1
    `;

    const params = [];

    if (date) {
      query += ` AND p.date = ?`;
      params.push(date);
    }

    if (strategy) {
      query += ` AND p.strategy = ?`;
      params.push(strategy);
    }

    // NEW: Add sentiment filter
    if (sentimentSignal) {
      query += ` AND p.contrarian_signal = ?`;
      params.push(sentimentSignal);
    }

    query += ` AND p.score >= ? AND p.iv_rank >= ? AND p.roi_30d >= ?`;
    params.push(minScore, minIVR, minROI);

    query += ` ORDER BY p.score DESC LIMIT ? OFFSET ?`;
    params.push(limit, offset);

    return this.db.prepare(query).all(...params);
  }

  /**
   * Get a single pick by ID
   */
  getPickById(id) {
    if (!this.db) throw new Error('Database not connected');

    const pick = this.db.prepare(`
      SELECT * FROM picks WHERE id = ?
    `).get(id);

    if (!pick) return null;

    // Get rationale if available
    const rationale = this.db.prepare(`
      SELECT summary FROM rationales
      WHERE pick_id = ?
      ORDER BY created_at DESC
      LIMIT 1
    `).get(id);

    return {
      ...pick,
      rationale: rationale?.summary || null
    };
  }

  /**
   * Get top picks across all dates
   */
  getTopPicks(limit = 10) {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT p.*, r.summary as rationale
      FROM picks p
      LEFT JOIN rationales r ON p.id = r.pick_id
        AND r.created_at = (
          SELECT MAX(created_at)
          FROM rationales
          WHERE pick_id = p.id
        )
      ORDER BY p.score DESC
      LIMIT ?
    `).all(limit);
  }

  /**
   * Get daily summary statistics
   */
  getDailySummary(date) {
    if (!this.db) throw new Error('Database not connected');

    // Count by strategy
    const counts = this.db.prepare(`
      SELECT strategy, COUNT(*) as count, AVG(score) as avg_score
      FROM picks
      WHERE date = ?
      GROUP BY strategy
    `).all(date);

    // Get top performers
    const topPicks = this.db.prepare(`
      SELECT symbol, strategy, roi_30d, score
      FROM picks
      WHERE date = ?
      ORDER BY score DESC
      LIMIT 5
    `).all(date);

    // Get overall stats
    const stats = this.db.prepare(`
      SELECT
        COUNT(*) as total_picks,
        AVG(score) as avg_score,
        AVG(roi_30d) as avg_roi,
        AVG(iv_rank) as avg_ivr
      FROM picks
      WHERE date = ?
    `).get(date);

    return {
      date,
      counts,
      topPicks,
      stats
    };
  }

  /**
   * Get historical performance data
   */
  getHistoricalData(days = 30) {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT
        date as date,
        strategy,
        COUNT(*) as count,
        AVG(score) as avg_score,
        AVG(roi_30d) as avg_roi
      FROM picks
      WHERE date >= date('now', '-' || ? || ' days')
      GROUP BY date, strategy
      ORDER BY date DESC
    `).all(days);
  }

  /**
   * Get available dates with picks
   */
  getAvailableDates() {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT DISTINCT date as date, COUNT(*) as count
      FROM picks
      GROUP BY date
      ORDER BY date DESC
    `).all();
  }

  /**
   * Get symbol performance history
   */
  getSymbolHistory(symbol) {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT *
      FROM picks
      WHERE symbol = ?
      ORDER BY date DESC
      LIMIT 30
    `).all(symbol);
  }

  /**
   * Search picks by symbol pattern
   */
  searchBySymbol(pattern) {
    if (!this.db) throw new Error('Database not connected');

    return this.db.prepare(`
      SELECT p.*, r.summary as rationale
      FROM picks p
      LEFT JOIN rationales r ON p.id = r.pick_id
        AND r.created_at = (
          SELECT MAX(created_at)
          FROM rationales
          WHERE pick_id = p.id
        )
      WHERE p.symbol LIKE ?
      ORDER BY p.date DESC, p.score DESC
      LIMIT 50
    `).all(`%${pattern}%`);
  }

  /**
   * Get aggregate statistics
   */
  getStats() {
    if (!this.db) throw new Error('Database not connected');

    const overall = this.db.prepare(`
      SELECT
        COUNT(*) as total_picks,
        COUNT(DISTINCT symbol) as unique_symbols,
        COUNT(DISTINCT date) as days_with_picks,
        AVG(score) as avg_score,
        AVG(roi_30d) as avg_roi,
        AVG(iv_rank) as avg_ivr
      FROM picks
    `).get();

    const byStrategy = this.db.prepare(`
      SELECT
        strategy,
        COUNT(*) as count,
        AVG(score) as avg_score,
        AVG(roi_30d) as avg_roi,
        AVG(iv_rank) as avg_ivr
      FROM picks
      GROUP BY strategy
    `).all();

    return {
      overall,
      byStrategy
    };
  }

  /**
   * Generic get method for monitoring routes (returns single row)
   */
  async get(query, params = []) {
    if (!this.db) throw new Error('Database not connected');
    return this.db.prepare(query).get(...params);
  }

  /**
   * Generic all method for monitoring routes (returns all rows)
   */
  async all(query, params = []) {
    if (!this.db) throw new Error('Database not connected');
    return this.db.prepare(query).all(...params);
  }

  /**
   * Generic run method for monitoring routes (executes without returning data)
   */
  async run(query, params = []) {
    if (!this.db) throw new Error('Database not connected');
    return this.db.prepare(query).run(...params);
  }

  /**
   * Close database connection
   */
  close() {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }
}

// Export singleton instance
export default new DatabaseService();