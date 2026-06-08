# ⏱️ Match Start Time - Blocking Predictions When Live

## Overview

The app now automatically **blocks predictions** for matches that have already started. It uses **Poland local time (CET/CEST)** to check if a match is currently live.

**Key features:**
- ✅ Automatically hides matches that have started
- ✅ Shows countdown to match kickoff
- ✅ Uses Poland timezone (Europe/Warsaw)
- ✅ Supports multiple time formats
- ✅ Backward compatible (works with or without start_time)

---

## Setup Instructions

### Step 1: Add `start_time` Column to Supabase

You need to add a `start_time` column to your `matches` table.

**Go to Supabase Dashboard → SQL Editor → New Query** and run:

```sql
ALTER TABLE matches 
ADD COLUMN start_time TIMESTAMP NULL;
```

Click **Run** to create the column.

### Step 2: Add Match Start Times

You can populate the start times in two ways:

#### Option A: Manual Entry (Easiest)
1. Go to **Supabase → Tables → matches**
2. Click each row and enter the start time in the `start_time` column
3. Use format: `2026-06-20 18:00:00` (YYYY-MM-DD HH:MM:SS)

#### Option B: SQL Insert
```sql
-- Example: Set start time for match ID 1
UPDATE matches 
SET start_time = '2026-06-20 18:00:00' 
WHERE id = 1;

-- Set multiple matches at once
UPDATE matches 
SET start_time = '2026-06-21 16:00:00' 
WHERE id IN (2, 3, 4);
```

### Step 3: Install Dependencies

Run in your terminal:

```bash
pip install pytz
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

---

## How It Works

### Time Check Logic

1. **User opens prediction form** → App reads current Poland time
2. **App compares** Poland time vs match start_time
3. **If current time ≥ match start_time** → Match is hidden from prediction list
4. **If current time < match start_time** → Match appears in dropdown

### Example Timeline

```
Match: Poland vs Argentina, Start: 2026-06-20 18:00 (Polish time)

17:30 Poland time → ✅ OPEN FOR PREDICTIONS (30 min remaining)
18:00 Poland time → 🔴 BLOCKED (match started)
19:45 Poland time → 🔴 BLOCKED (match in progress)
20:30 Poland time → 🔴 BLOCKED (match finished, results entered)
```

### Timezone

- **Timezone used:** Europe/Warsaw (Poland local time)
- **Daylight Saving:** Automatically applied (CET/CEST)
- **World Cup 2026 in USA:** Times are converted to Poland timezone automatically

---

## Time Formats Supported

The app accepts these time formats:

```
✅ 2026-06-20 18:00:00   (YYYY-MM-DD HH:MM:SS)
✅ 2026-06-20 18:00      (YYYY-MM-DD HH:MM)
✅ 20-06-2026 18:00:00   (DD-MM-YYYY HH:MM:SS)
✅ 20-06-2026 18:00      (DD-MM-YYYY HH:MM)
✅ 2026-06-20T18:00:00Z  (ISO 8601)
```

---

## User Interface Changes

### Before Match Starts
```
⚽ Obstaw mecz

Wybierz mecz:
  ▼ Mecz 1: Poland vs Argentina
  ▼ Mecz 2: Germany vs Spain
  [Zapisz mój typ]
```

### After Match Starts
```
⏱️ 2 mecze już się rozpoczęły - nie możesz typować.

🔴 Mecz 1: Poland vs Argentina
🔴 Mecz 2: Germany vs Spain

Dostępne do typowania:
  ▼ Mecz 3: France vs Brazil
```

---

## Troubleshooting

### Error: "Błąd przy sprawdzaniu czasu meczu"
→ Check time format is correct (YYYY-MM-DD HH:MM:SS)
→ Make sure the time is valid

### All matches hidden but should be available
→ Check Poland current time vs match times in Supabase
→ Verify `start_time` column exists and has data

### Predictions still open for live match
→ Ensure `start_time` is set for that match
→ Check the timezone - times should be in Poland local time
→ Refresh the browser (Streamlit cache)

### Empty dropdown when matches available
→ Make sure at least one match has `start_time < current_poland_time`
→ Check that matches have no result yet (homeGoals/awayGoals empty)

---

## Examples

### Setting up World Cup 2026 Schedule

World Cup 2026 is in USA (multiple time zones). Convert to Poland time:

```
USA PST (Pacific):   14:00 → Poland CET: 23:00 (next day)
USA CST (Central):   16:00 → Poland CET: 01:00 (next day)
USA EST (Eastern):   18:00 → Poland CET: 03:00 (next day)
```

**Example SQL:**
```sql
-- Group stage matches
UPDATE matches SET start_time = '2026-06-11 23:00:00' WHERE id = 1;  -- USA PST 14:00
UPDATE matches SET start_time = '2026-06-12 01:00:00' WHERE id = 2;  -- USA CST 16:00
UPDATE matches SET start_time = '2026-06-12 03:00:00' WHERE id = 3;  -- USA EST 18:00
```

---

## Database Backup

Before making changes, backup your matches table:

```sql
-- Create a backup
CREATE TABLE matches_backup AS SELECT * FROM matches;

-- If something goes wrong, restore:
DROP TABLE matches;
CREATE TABLE matches AS SELECT * FROM matches_backup;
```

---

## Notes

- ⏰ Times are automatically converted from USA zones to Poland time (Europe/Warsaw)
- 🔄 The app checks time every time the page loads (no need to refresh manually)
- 📱 Works on all devices (mobile, desktop, tablet)
- 🌍 Always uses Poland timezone, regardless of user's local timezone

Done! Your predictions are now time-locked to match kickoff times. 🏆⏱️
