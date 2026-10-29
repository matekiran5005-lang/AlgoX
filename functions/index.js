const functions = require('firebase-functions');
const admin = require('firebase-admin');
const express = require('express');

admin.initializeApp();
const app = express();
app.use(express.json());

app.get('/health', (req, res) => res.json({ status: 'ok' }));

// TODO: migrate all /api/* routes from app.py here
// Dhan fund limit example:
app.get('/dashboard/:userId', async (req, res) => {
  res.json({ status: 'ok', message: 'Migrate from app.py' });
});

exports.api = functions.https.onRequest(app);