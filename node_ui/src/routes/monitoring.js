/**
 * Monitoring API endpoints for health checks and performance metrics.
 */

import express from 'express';
import db from '../db.js';

const router = express.Router();

/**
 * GET /api/monitoring/health
 * Get current system health status
 */
router.get('/health', async (req, res) => {
    try {
        // Get last run
        const lastRun = await db.get(`
            SELECT id, run_date, started_at, completed_at, status,
                   symbols_attempted, symbols_succeeded, symbols_failed,
                   total_picks, duration_seconds
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT 1
        `);

        // Get success rate (last 7 days)
        const weekStats = await db.get(`
            SELECT
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs
            FROM pipeline_runs
            WHERE started_at >= datetime('now', '-7 days')
        `);

        // Get recent alerts
        const recentAlerts = await db.get(`
            SELECT COUNT(*) as count
            FROM monitoring_alerts
            WHERE created_at >= datetime('now', '-24 hours')
            AND severity IN ('warning', 'critical')
        `);

        // Calculate health score
        let healthScore = 100;
        let status = 'healthy';

        if (lastRun) {
            const lastRunTime = new Date(lastRun.started_at);
            const hoursSinceRun = (Date.now() - lastRunTime.getTime()) / (1000 * 60 * 60);

            if (hoursSinceRun > 26) {
                healthScore -= 50;
                status = 'critical';
            } else if (lastRun.status === 'failed') {
                healthScore -= 30;
                status = 'degraded';
            }

            // Check symbol success rate
            if (lastRun.symbols_attempted > 0) {
                const successRate = lastRun.symbols_succeeded / lastRun.symbols_attempted;
                if (successRate < 0.5) {
                    healthScore -= 20;
                    if (status === 'healthy') {
                        status = 'degraded';
                    }
                }
            }
        } else {
            healthScore = 0;
            status = 'critical';
        }

        // Weekly success rate
        let weeklySuccessRate = 0;
        if (weekStats && weekStats.total_runs > 0) {
            weeklySuccessRate = (weekStats.successful_runs / weekStats.total_runs) * 100;
            if (weeklySuccessRate < 80) {
                healthScore -= 15;
            }
        }

        // Recent alerts
        const alertCount = recentAlerts ? recentAlerts.count : 0;
        if (alertCount > 5) {
            healthScore -= 10;
        }

        healthScore = Math.max(0, healthScore);

        res.json({
            success: true,
            status,
            health_score: healthScore,
            last_run: lastRun || null,
            weekly_stats: {
                total_runs: weekStats?.total_runs || 0,
                successful_runs: weekStats?.successful_runs || 0,
                success_rate: weeklySuccessRate
            },
            recent_alerts_24h: alertCount,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('Health check error:', error);
        res.status(500).json({
            success: false,
            error: error.message,
            status: 'unknown',
            health_score: 0
        });
    }
});

/**
 * GET /api/monitoring/runs
 * Get recent pipeline runs
 */
router.get('/runs', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 10;
        const offset = parseInt(req.query.offset) || 0;

        const runs = await db.all(`
            SELECT id, run_date, started_at, completed_at, status,
                   symbols_attempted, symbols_succeeded, symbols_failed,
                   total_picks, cc_picks, csp_picks, api_calls,
                   duration_seconds, error_message
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
        `, [limit, offset]);

        const total = await db.get('SELECT COUNT(*) as count FROM pipeline_runs');

        res.json({
            success: true,
            count: runs.length,
            total: total.count,
            runs
        });

    } catch (error) {
        console.error('Runs query error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/monitoring/performance
 * Get performance metrics summary
 */
router.get('/performance', async (req, res) => {
    try {
        const days = parseInt(req.query.days) || 7;

        const stats = await db.get(`
            SELECT
                AVG(duration_seconds) as avg_duration,
                MIN(duration_seconds) as min_duration,
                MAX(duration_seconds) as max_duration,
                AVG(api_calls) as avg_api_calls,
                AVG(total_picks) as avg_picks,
                COUNT(*) as total_runs
            FROM pipeline_runs
            WHERE started_at >= datetime('now', '-' || ? || ' days')
            AND status = 'success'
        `, [days]);

        res.json({
            success: true,
            period_days: days,
            total_runs: stats?.total_runs || 0,
            avg_duration_seconds: stats?.avg_duration ? Math.round(stats.avg_duration * 100) / 100 : 0,
            min_duration_seconds: stats?.min_duration ? Math.round(stats.min_duration * 100) / 100 : 0,
            max_duration_seconds: stats?.max_duration ? Math.round(stats.max_duration * 100) / 100 : 0,
            avg_api_calls: stats?.avg_api_calls ? Math.round(stats.avg_api_calls * 100) / 100 : 0,
            avg_picks: stats?.avg_picks ? Math.round(stats.avg_picks * 100) / 100 : 0
        });

    } catch (error) {
        console.error('Performance query error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/monitoring/alerts
 * Get recent monitoring alerts
 */
router.get('/alerts', async (req, res) => {
    try {
        const limit = parseInt(req.query.limit) || 20;
        const severity = req.query.severity; // 'critical', 'warning', 'info'

        let query = `
            SELECT id, alert_type, severity, message, details,
                   sent_via, acknowledged, created_at
            FROM monitoring_alerts
        `;

        const params = [];
        if (severity) {
            query += ' WHERE severity = ?';
            params.push(severity);
        }

        query += ' ORDER BY created_at DESC LIMIT ?';
        params.push(limit);

        const alerts = await db.all(query, params);

        res.json({
            success: true,
            count: alerts.length,
            alerts: alerts.map(alert => ({
                ...alert,
                details: alert.details ? JSON.parse(alert.details) : null
            }))
        });

    } catch (error) {
        console.error('Alerts query error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * POST /api/monitoring/alerts/:id/acknowledge
 * Acknowledge an alert
 */
router.post('/alerts/:id/acknowledge', async (req, res) => {
    try {
        const { id } = req.params;

        await db.run(`
            UPDATE monitoring_alerts
            SET acknowledged = 1
            WHERE id = ?
        `, [id]);

        res.json({
            success: true,
            message: 'Alert acknowledged'
        });

    } catch (error) {
        console.error('Alert acknowledge error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/monitoring/metrics/:runId
 * Get specific metrics for a run
 */
router.get('/metrics/:runId', async (req, res) => {
    try {
        const { runId } = req.params;

        const metrics = await db.all(`
            SELECT metric_name, metric_value, metric_unit, recorded_at
            FROM performance_metrics
            WHERE run_id = ?
            ORDER BY recorded_at DESC
        `, [runId]);

        res.json({
            success: true,
            run_id: runId,
            count: metrics.length,
            metrics
        });

    } catch (error) {
        console.error('Metrics query error:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

export default router;
