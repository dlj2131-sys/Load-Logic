const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;
const SUBMISSIONS_DIR = path.join(__dirname, 'submissions');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(__dirname));

if (!fs.existsSync(SUBMISSIONS_DIR)) {
  fs.mkdirSync(SUBMISSIONS_DIR, { recursive: true });
}

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'Landing page - Design 5 - Modular Grid.html'));
});

app.post('/api/booking', (req, res) => {
  try {
    const data = req.body;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `booking-${timestamp}.json`;
    const filepath = path.join(SUBMISSIONS_DIR, filename);

    fs.writeFileSync(filepath, JSON.stringify(data, null, 2), 'utf8');

    res.status(200).json({
      success: true,
      message: 'Booking request received. We will contact you shortly.',
      id: filename
    });
  } catch (err) {
    console.error('Error saving booking:', err);
    res.status(500).json({
      success: false,
      message: 'Something went wrong. Please try again or call us.'
    });
  }
});

app.listen(PORT, () => {
  console.log(`Load Logic site running at http://localhost:${PORT}`);
  console.log(`Form submissions are saved to: ${SUBMISSIONS_DIR}`);
});
