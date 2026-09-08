# Laptop Sales Copilot

A private local web app for a laptop salesperson.

It takes a customer's Arabic / Egyptian Arabic / English request, understands the use case and budget, filters **only in-stock laptops**, scores the best matches, and can generate a WhatsApp-ready sales message.

## What is already implemented

- Seed inventory extracted from the supplied `El-mostawred.pdf` (38 rows).
- CSV / Excel inventory import.
- Google Sheets live inventory:
  - public / link-accessible sheet via CSV export;
  - private Google Sheet via a Google service-account JSON file.
- Arabic + English intent parsing.
- Budget parsing (`30 ألف`, `30k`, ranges, etc.).
- Multi-use-case detection: Gaming, Programming, Engineering, Architecture, Video Editing, Photoshop/Design, AI/ML, Office.
- CPU/GPU/RAM/SSD normalization and scoring.
- Stock filtering (`qty > 0` only).
- Best-match ranking with a controlled 15% budget stretch when no exact result exists.
- 100% FREE local Ollama AI for intent parsing and persuasive WhatsApp messages.
- Deterministic fallback parser and message template if Ollama is not running.
- Optional local password.

## Fastest way to run on macOS

```bash
cd laptop-sales-copilot

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

streamlit run app.py
```

Your browser should open automatically. If not, use the local URL printed by Streamlit.


## Enable the FREE local AI

Recommended model:

```bash
ollama pull qwen3:30b-instruct
```

Or simply run:

```bash
./install_local_ai.command
```

Then start the app:

```bash
./setup_and_run.command
```

No API key, paid account, or per-message cost is required.

The default model can be changed in `.env`:

```env
OLLAMA_MODEL=qwen3:30b-instruct
OLLAMA_NUM_CTX=8192
```

For a faster/lighter option, use:

```bash
ollama pull qwen3:14b
```

and set:

```env
OLLAMA_MODEL=qwen3:14b
```

## Connect your actual Google Sheet

In the sidebar select **Google Sheet**.

### Option A — sheet accessible by link / public export

Paste the normal Google Sheets URL. The app converts it to a CSV export URL automatically.

### Option B — private sheet

1. Create a Google Cloud service account.
2. Enable Google Sheets API.
3. Download its JSON credentials.
4. Share your sheet with the service-account email.
5. Put the JSON file somewhere safe on your Mac.
6. In the app, paste:
   - the normal Google Sheet URL;
   - worksheet/tab name if needed;
   - the full local path to the JSON file.

Do **not** commit the service-account JSON to Git.

## Expected inventory columns

The app recognizes Arabic and English aliases for:

- `model` / الموديل
- `specs` / المواصفات
- `qty` / العدد
- `screen_inches` / الشاشة
- `price_egp` / السعر
- `camera` / الكاميرا

At minimum, `model` and `specs` are required.

## Important design rule

The AI does not invent the winning laptop. It extracts the customer's needs; the recommendation engine filters and ranks actual inventory rows. The AI then explains or writes the sales message using only supplied product facts.


## ITI API setup (recommended)

This build can use the ITI Student API as the primary AI provider.

Create `.env` from the example:

```bash
cp .env.example .env
```

Then add your **new/rotated** API key:

```env
ITI_BASE_URL=http://apiaccess.iti.net.eg/api/v1
ITI_MODEL=deepseek.v3.2
SBG_API_KEY=YOUR_NEW_KEY_HERE
```

Never commit `.env`.

Provider priority:

1. ITI Student API / DeepSeek V3.2
2. Ollama local model
3. Deterministic local parser/template

The ITI integration uses:

```text
POST /student/chat
Authorization: Bearer <SBG_API_KEY>
```

with `model_id`, `messages`, and `system_prompt`.
