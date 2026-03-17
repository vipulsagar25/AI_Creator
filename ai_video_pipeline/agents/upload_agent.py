"""
agents/upload_agent.py
=======================
Uploads final video to YouTube using the official YouTube Data API v3.
Requires one-time OAuth2 setup (free, no paid plan needed).

Setup:
  1. Go to https://console.cloud.google.com
  2. Create project → Enable YouTube Data API v3
  3. Create OAuth2 credentials → Download client_secret.json
  4. Run this script once → browser opens → authenticate → token saved
"""

import logging
import os
from pathlib import Path
from typing import Optional

from config import PipelineConfig

logger = logging.getLogger("upload_agent")

# Optional imports — only needed if uploading
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import pickle
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    logger.warning("YouTube upload deps not installed. Run: pip install google-api-python-client google-auth-oauthlib")


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE  = "credentials/youtube_token.pickle"
SECRET_FILE = "credentials/client_secret.json"


class UploadAgent:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.youtube = None

    def authenticate(self):
        """OAuth2 flow — opens browser on first run, uses cached token after."""
        if not YOUTUBE_AVAILABLE:
            raise ImportError("Install: pip install google-api-python-client google-auth-oauthlib")

        creds = None
        if Path(TOKEN_FILE).exists():
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            Path(TOKEN_FILE).parent.mkdir(exist_ok=True)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)

        self.youtube = build("youtube", "v3", credentials=creds)
        logger.info("YouTube: authenticated")

    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list] = None,
        category_id: str = "22",       # 22 = People & Blogs
        privacy: str = "private",      # private | unlisted | public
    ) -> str:
        """Upload video to YouTube. Returns video URL."""
        if not self.youtube:
            self.authenticate()

        tags = tags or []
        body = {
            "snippet": {
                "title":       title,
                "description": description,
                "tags":        tags,
                "categoryId":  category_id,
            },
            "status": {
                "privacyStatus": privacy,
            },
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info(f"Uploading: {video_path}")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id  = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"✅ Uploaded: {video_url}")
        return video_url
