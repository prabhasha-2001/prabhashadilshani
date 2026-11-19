import io
from pathlib import Path

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 128
PDF_BYTES = b"%PDF-1.4\n" + b"0" * 128


def test_media_upload_and_delete(client, auth):
    response = client.post(
        "/api/v1/admin/media",
        headers=auth,
        data={"file": (io.BytesIO(PNG_BYTES), "photo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    media = response.get_json()["data"]
    assert media["mime_type"] == "image/png"
    assert media["url"].startswith("/uploads/media/")

    listing = client.get("/api/v1/admin/media", headers=auth).get_json()["data"]
    assert len(listing) == 1

    assert client.delete(f"/api/v1/admin/media/{media['id']}", headers=auth).status_code == 200
    assert client.get("/api/v1/admin/media", headers=auth).get_json()["data"] == []


def test_upload_rejects_disallowed_extension(client, auth):
    response = client.post(
        "/api/v1/admin/media",
        headers=auth,
        data={"file": (io.BytesIO(b"hello"), "script.exe")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "unsupported_media_type"


def test_upload_rejects_mismatched_content(client, auth):
    response = client.post(
        "/api/v1/admin/media",
        headers=auth,
        data={"file": (io.BytesIO(b"not really a png"), "fake.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415


def test_resume_upload_default_and_download(client, auth):
    first = client.post(
        "/api/v1/admin/resumes",
        headers=auth,
        data={"label": "Data CV", "is_default": "true", "file": (io.BytesIO(PDF_BYTES), "cv.pdf")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 201, first.get_json()
    resume = first.get_json()["data"]
    assert resume["is_default"] is True

    second = client.post(
        "/api/v1/admin/resumes",
        headers=auth,
        data={"label": "ML CV", "is_default": "true", "file": (io.BytesIO(PDF_BYTES), "cv2.pdf")},
        content_type="multipart/form-data",
    )
    assert second.status_code == 201

    resumes = client.get("/api/v1/admin/resumes", headers=auth).get_json()["data"]
    defaults = [item for item in resumes if item["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["label"] == "ML CV"

    download = client.get(f"/api/v1/resumes/{resume['id']}/download")
    assert download.status_code == 200
    url = download.get_json()["data"]["download_url"]
    file_response = client.get(url)
    assert file_response.status_code == 200
    assert file_response.mimetype == "application/pdf"


def test_resume_requires_pdf(client, auth):
    response = client.post(
        "/api/v1/admin/resumes",
        headers=auth,
        data={"label": "Fake CV", "file": (io.BytesIO(PNG_BYTES), "cv.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415

def test_profile_resume_upload_publishes_to_public_profile(client, auth, app):
    original = client.get("/api/v1/admin/profile", headers=auth).get_json()["data"]
    response = client.post(
        "/api/v1/admin/profile/resume",
        headers=auth,
        data={"file": (io.BytesIO(PDF_BYTES), "resume.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()["data"]
    url = payload["url"]
    assert url.startswith("/uploads/resumes/")
    assert payload["filename"] == "resume.pdf"
    assert payload["previous_url"] == original.get("resume_url")

    saved_file = Path(app.config["UPLOAD_DIR"]) / url.removeprefix("/uploads/")
    assert saved_file.is_file()
    assert saved_file.read_bytes().startswith(b"%PDF-")
    assert saved_file.name != "resume.pdf"

    admin_profile = client.get("/api/v1/admin/profile", headers=auth).get_json()["data"]
    assert admin_profile["resume_url"] == url
    assert admin_profile["full_name"] == original["full_name"]
    assert admin_profile["avatar_url"] == original.get("avatar_url")

    public_profile = client.get("/api/v1/profile").get_json()["data"]
    assert public_profile["resume_url"] == url
    assert public_profile["full_name"] == original["full_name"]

    pdf = client.get(url)
    assert pdf.status_code == 200
    assert pdf.mimetype == "application/pdf"
    assert pdf.data.startswith(b"%PDF-")


def test_profile_resume_rejects_unsafe_files(client, auth):
    oversized = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024)
    cases = [
        ("photo.jpg", PNG_BYTES, "image/jpeg", 415),
        ("photo.png", PNG_BYTES, "image/png", 415),
        ("malware.exe", b"MZ\x90\x00", "application/octet-stream", 415),
        ("fake.pdf", b"not really a pdf", "application/pdf", 415),
        ("mismatch.pdf", PDF_BYTES, "image/png", 415),
        ("large.pdf", oversized, "application/pdf", 413),
    ]
    for filename, content, mimetype, expected_status in cases:
        response = client.post(
            "/api/v1/admin/profile/resume",
            headers=auth,
            data={"file": (io.BytesIO(content), filename, mimetype)},
            content_type="multipart/form-data",
        )
        assert response.status_code == expected_status, (filename, response.get_json())


def test_profile_resume_sanitizes_filename_and_keeps_previous_file(client, auth, app):
    first = client.post(
        "/api/v1/admin/profile/resume",
        headers=auth,
        data={"file": (io.BytesIO(PDF_BYTES), "first.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 201, first.get_json()
    first_url = first.get_json()["data"]["url"]

    second = client.post(
        "/api/v1/admin/profile/resume",
        headers=auth,
        data={"file": (io.BytesIO(PDF_BYTES), "../../unsafe resume.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert second.status_code == 201, second.get_json()
    second_url = second.get_json()["data"]["url"]
    assert second_url.startswith("/uploads/resumes/")
    stored_name = second_url.rsplit("/", 1)[-1]
    assert "/" not in stored_name and "\\" not in stored_name and ".." not in stored_name
    assert stored_name.endswith(".pdf")
    assert first_url != second_url

    upload_dir = Path(app.config["UPLOAD_DIR"])
    assert (upload_dir / first_url.removeprefix("/uploads/")).is_file()
    assert (upload_dir / second_url.removeprefix("/uploads/")).is_file()
