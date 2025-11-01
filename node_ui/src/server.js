import express from 'express';
import cors from 'cors';
import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(cors());
app.use(express.json());

// Adjust path as needed in prod
const DB_PATH = process.env.DB_PATH || path.resolve(__dirname, '../../data/screener.db');
let db;
try {
  db = new Database(DB_PATH, { readonly: true });
} catch (e) {
  console.warn('DB open failed:', e.message);
}

// static UI (if you later build a front-end)
app.use(express.static(path.resolve(__dirname, '../public')));

app.get('/api/healthz', (req, res) => res.json({ ok: true }));

app.get('/api/latest-date', (req, res) => {
  try {
    const row = db.prepare('SELECT MAX(asof) as latest FROM picks').get();
    res.json(row || { latest: null });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/picks', (req, res) => {
  const { date, strategy, minScore = 0, minIVR = 0, minROI = 0 } = req.query;
  try {
    let q = `SELECT * FROM picks WHERE 1=1`;
    const params = {};
    if (date) { q += ` AND asof=@date`; params.date = date; }
    if (strategy) { q += ` AND strategy=@strategy`; params.strategy = strategy; }
    q += ` AND (score >= @minScore) AND (iv_rank >= @minIVR) AND (roi_30d >= @minROI)`;
    q += ` ORDER BY score DESC LIMIT 500`;
    const rows = db.prepare(q).all({ ...params, minScore: Number(minScore), minIVR: Number(minIVR), minROI: Number(minROI) });
    res.json(rows);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/pick/:id', (req, res) => {
  try {
    const pick = db.prepare('SELECT * FROM picks WHERE id=?').get(req.params.id);
    if (!pick) return res.status(404).json({ error: 'not found' });
    const rationale = db.prepare('SELECT summary FROM rationales WHERE pick_id=? ORDER BY created_at DESC LIMIT 1').get(req.params.id);
    res.json({ pick, rationale: rationale?.summary || null });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`UI listening on http://localhost:${PORT}`));
