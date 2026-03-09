# LexFlow — Privacy & Data Handling

## Architecture

LexFlow uses **Supabase** (hosted PostgreSQL with Row Level Security) as its database.
All billing data is stored in Supabase's cloud infrastructure and is scoped to each
authenticated user via Row Level Security (RLS) policies.

## Data Flow

1. **Audio Input** — Voice recordings are captured in the browser or uploaded as files
2. **Processing** — Audio is sent to Google Gemini for transcription and entity extraction
3. **Immediate Deletion** — Temporary audio files and Gemini uploads are deleted immediately
   after processing (POPIA compliance)
4. **Human Review** — Extracted billing data is presented for user review before saving
5. **Storage** — Approved entries are stored in Supabase PostgreSQL with RLS enforcement

## POPIA Compliance

- Audio files are never persisted on disk beyond the transcription request
- Gemini file uploads are explicitly deleted after each extraction
- No audio data is retained in any database or file system
- Users can delete individual billing entries at any time

## Row Level Security

Each user can only access their own data. The backend passes the user's JWT token
to Supabase, ensuring RLS policies are enforced at the database level. The service
role key is used only for admin operations (demo data seeding) and is never exposed
to the browser.

## Third-Party Services

| Service | Purpose | Data Shared |
|---------|---------|-------------|
| **Google Gemini** | Audio transcription + entity extraction | Audio file (deleted after processing) |
| **Supabase** | Authentication + database | User profile, billing entries |
| **Render** | Hosting | Application code only |

## Contact

For privacy inquiries: [tshepisojafta@outlook.com](mailto:tshepisojafta@outlook.com)
