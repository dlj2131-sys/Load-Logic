# Load Logic – Landing Page & Booking

Run the site locally and save form submissions to files.

## Run the website

1. **Install dependencies**
   ```bash
   npm install
   ```

2. **Start the server**
   ```bash
   npm start
   ```

3. **Open in browser**
   - Go to **http://localhost:3000**

## Form submissions

When someone submits the **Oil Service Request** form:

- The data is sent to `POST /api/booking`.
- Each submission is saved as a JSON file in the **`submissions/`** folder.
- Files are named like `booking-2025-01-15T12-30-45-123Z.json` and contain all form fields (name, phone, address, fuel type, quantity, delivery date, etc.).

You can process these JSON files with another script, import them into a spreadsheet, or send them to another system.

## Project layout

- `Landing page - Design 5 - Modular Grid.html` – main landing page
- `server.js` – Express server (serves the site + booking API)
- `submissions/` – directory where booking JSON files are stored (created automatically)
