from io import StringIO
from pathlib import Path
from typing import Self, cast

import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.http import MediaFileUpload  # type: ignore
from gspread_pandas import Client, Spread  # type: ignore

from requipso import BASE_DIR

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
CLIENT_SECRET_PATH = BASE_DIR / "google_oauth_client.json"
TOKEN_PATH = Path.home() / ".config" / "requipso" / "google_token.json"


def get_user_credentials(
    client_secret_path: Path = CLIENT_SECRET_PATH,
    token_path: Path = TOKEN_PATH,
) -> Credentials:
    """Return the user's Google credentials, opening a browser login if needed.

    The token is cached in ``token_path``; delete it to log in with another account.
    """
    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


class GoogleConnector:
    def __init__(
        self,
        folder_id: str = "1vTA1zVLbyU6mVMkiTL1J1bLolOlsut7A",
        credentials: Credentials | None = None,
    ):
        self.folder_id = folder_id
        self.credentials = credentials or get_user_credentials()

        # Build Drive service
        self.service = build("drive", "v3", credentials=self.credentials)

        self.sheets = self.list_sheets()

        self.spreadsheet_name: str | None = None
        self.spreadsheet_key: str | None = None
        self.spread: Spread | None = None

    def set_spreadsheet(self, spreadsheet_name: str) -> Self:
        self.spreadsheet_name = spreadsheet_name
        self.spreadsheet_key = self.sheets.get(self.spreadsheet_name)
        if self.spreadsheet_key is None:
            raise ValueError(
                f"Spreadsheet {self.spreadsheet_name} not found. Available spreadsheets: {self.sheets.keys()}"
            )
        self.spread = self.open_spread()
        return self

    def open_sheet(self, sheet_name: str, header_rows: int = 1) -> pd.DataFrame:
        """Read a worksheet through CSV so pandas handles parsing consistently."""
        if self.spread is None:
            raise ValueError("Spreadsheet not open")
        df = self.spread.sheet_to_df(
            sheet=sheet_name,
            index=False,
            header_rows=header_rows,
        )
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        df = pd.read_csv(csv_buffer)
        df = df.where(pd.notna(df), None)

        return cast(pd.DataFrame, df)

    def list_sheets(self) -> dict[str, str]:
        results = (
            self.service.files()
            .list(
                q=f"'{self.folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])

        return {f["name"]: f["id"] for f in files}

    def open_spread(self) -> Spread:
        """Return a :class:`Spread` for the current spreadsheet."""
        client = Client(creds=self.credentials)
        return Spread(spread=self.spreadsheet_key, client=client)

    def upload_file(self, file_path: Path, upload_name: str | None = None) -> str:
        # 1. Search for existing file
        upload_name = upload_name or file_path.name
        query = (
            f"'{self.folder_id}' in parents and name='{upload_name}' and trashed=false"
        )

        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )

        files = results.get("files", [])

        media = MediaFileUpload(file_path)

        if files:
            # File exists → UPDATE it
            file_id = files[0]["id"]

            _ = (
                self.service.files()
                .update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True,
                )
                .execute()
            )

            print("File replaced:", file_id)

        else:
            # File does not exist → CREATE it
            file_metadata = {"name": upload_name, "parents": [self.folder_id]}

            created = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                    supportsAllDrives=True,
                )
                .execute()
            )
            file_id = created["id"]
            print("File uploaded:", file_id)

        url = f"https://drive.google.com/file/d/{file_id}/view?usp=drive_link"
        return url
