# Instagram UI Trigger API Documentation

You can trigger the AI generation pipelines manually across the application without needing passwords, API keys, or waiting for the schedule timer.

These are native `GET` requests, meaning you can trigger them simply by opening the URL in your browser, or hitting them smoothly from Make.com, postman, and iOS Shortcuts.

All generation happens asynchronously in the background.

## Available Triggers:

> [!TIP]
> **Base URL:** Your active domain (e.g. your ngrok url or your render server url). Examples below use your local API `https://instagram-automation-g7b4.onrender.com/api/v1`

| Action | Endpoint URL | Behavior |
| --- | --- | --- |
| **Post AI Image to Feed** | `GET https://instagram-automation-g7b4.onrender.com/api/v1/trigger/feed/image` | Generates a new nature image, writes a caption, and uploads it to the Feed. (Will *also* add it to your story if `story_automation` is ON). |
| **Post AI Reel to Feed** | `GET https://instagram-automation-g7b4.onrender.com/api/v1/trigger/feed/video` | Generates a completely new 4-scene video script via AI, renders the Reel, and uploads to Feed. |
| **Post AI Image exclusively to Story** | `GET https://instagram-automation-g7b4.onrender.com/api/v1/trigger/story/image` | Generates an image and uploads it *straight* to the native Story feed. It bypasses your Feed entirely. |
| **Post AI Reel exclusively to Story** | `GET https://instagram-automation-g7b4.onrender.com/api/v1/trigger/story/video` | Renders a brand new reel video and uploads it directly as a full-screen video to your Story. Bypasses Feed. |
| **Trigger Auto-Commenter** | `GET https://instagram-automation-g7b4.onrender.com/api/v1/trigger/comments` | Immediately wakes up the AI comment engine to analyze missing replies and generate personalized responses instantly. |

---

### Example: Running a trigger via Terminal
```bash
curl -X GET "https://instagram-automation-g7b4.onrender.com/api/v1/trigger/story/image"
```

### Example: Running via Browser
Simply open your web browser and navigate directly to:
`https://instagram-automation-g7b4.onrender.com/api/v1/trigger/comments`
