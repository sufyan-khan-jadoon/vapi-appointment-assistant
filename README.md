---
title: Vapi Appointment Assistant
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Vapi Appointment Assistant Backend

This is the FastAPI backend for the Vapi-powered clinic appointment assistant. 
It connects to a Supabase PostgreSQL database to manage patient appointments.

## Deployment on Hugging Face Spaces
1. Create a new **Space** on Hugging Face.
2. Select **Docker** as the SDK.
3. Upload these files or connect your GitHub.
4. **IMPORTANT:** Go to the Space **Settings** -> **Variables and secrets**.
5. Add a **Secret** named `DATABASE_URL` with your Supabase connection string:
   `postgresql://postgres:khanbaba%401234@db.ttmqqtgkooubledirlzc.supabase.co:5432/postgres`

## Vapi Configuration
Once the Space is "Running", copy the URL (e.g., `https://username-space-name.hf.space`).
In your Vapi Dashboard, set the **Server URL** to:
`https://username-space-name.hf.space/vapi-webhook/`
