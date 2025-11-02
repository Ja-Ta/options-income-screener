/**
 * Options Income Screener API Server
 * Provides REST endpoints for accessing screening results
 */

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

// Import route modules
import picksRoutes from './routes/picks.js';
import statsRoutes from './routes/stats.js';
import symbolsRoutes from './routes/symbols.js';
import monitoringRoutes from './routes/monitoring.js';
import db from './db.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Request logging middleware
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Static files (for future frontend)
app.use(express.static(path.resolve(__dirname, '../public')));

// Health check endpoint
app.get('/api/health', (req, res) => {
  const isDbConnected = db.isConnected();
  const status = isDbConnected ? 'healthy' : 'unhealthy';

  res.status(isDbConnected ? 200 : 503).json({
    status,
    service: 'Options Income Screener API',
    version: '1.0.0',
    database: isDbConnected ? 'connected' : 'disconnected',
    timestamp: new Date().toISOString()
  });
});

// API Routes
app.use('/api/picks', picksRoutes);
app.use('/api/stats', statsRoutes);
app.use('/api/symbols', symbolsRoutes);
app.use('/api/monitoring', monitoringRoutes);

// API documentation endpoint
app.get('/api', (req, res) => {
  res.json({
    name: 'Options Income Screener API',
    version: '1.0.0',
    endpoints: {
      health: {
        GET: '/api/health - Service health check'
      },
      picks: {
        GET: '/api/picks - Get filtered picks',
        'GET /latest': '/api/picks/latest - Get picks from most recent date',
        'GET /top': '/api/picks/top - Get top picks across all dates',
        'GET /date/:date': '/api/picks/date/:date - Get picks for specific date',
        'GET /:id': '/api/picks/:id - Get single pick by ID'
      },
      stats: {
        GET: '/api/stats - Get overall statistics',
        'GET /daily/:date': '/api/stats/daily/:date - Get daily summary',
        'GET /history': '/api/stats/history - Get historical performance',
        'GET /dates': '/api/stats/dates - Get available dates',
        'GET /latest-date': '/api/stats/latest-date - Get latest date'
      },
      symbols: {
        'GET /search': '/api/symbols/search?q=AAPL - Search picks by symbol',
        'GET /:symbol/history': '/api/symbols/:symbol/history - Get symbol history'
      },
      monitoring: {
        'GET /health': '/api/monitoring/health - System health status with score',
        'GET /runs': '/api/monitoring/runs - Recent pipeline executions',
        'GET /performance': '/api/monitoring/performance - Performance metrics summary',
        'GET /alerts': '/api/monitoring/alerts - Recent monitoring alerts',
        'POST /alerts/:id/acknowledge': '/api/monitoring/alerts/:id/acknowledge - Acknowledge alert',
        'GET /metrics/:runId': '/api/monitoring/metrics/:runId - Metrics for specific run'
      }
    },
    queryParameters: {
      picks: {
        date: 'YYYY-MM-DD format',
        strategy: 'CC or CSP',
        minScore: 'Minimum score (0-1)',
        minIVR: 'Minimum IV Rank (0-100)',
        minROI: 'Minimum ROI (decimal)',
        limit: 'Max results (default 100)',
        offset: 'Pagination offset'
      }
    }
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: 'Endpoint not found',
    path: req.path
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err);
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    message: err.message
  });
});

// Start server
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';  // Bind to all interfaces for external access

app.listen(PORT, HOST, () => {
  console.log('================================================');
  console.log('   Options Income Screener API Server');
  console.log('================================================');
  console.log(`   Server:   http://${HOST}:${PORT}`);
  console.log(`   API Docs: http://${HOST}:${PORT}/api`);
  console.log(`   Health:   http://${HOST}:${PORT}/api/health`);
  console.log(`   Database: ${db.isConnected() ? '✅ Connected' : '❌ Disconnected'}`);
  console.log('================================================');
  console.log('\n   Access from external IP:');
  console.log(`   http://YOUR_DROPLET_IP:${PORT}`);
  console.log('================================================');
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down gracefully...');
  db.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Shutting down gracefully...');
  db.close();
  process.exit(0);
});
