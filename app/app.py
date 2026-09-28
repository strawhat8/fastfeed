import base64
import hashlib
import hmac
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import User, create_db_and_tables, get_async_session, posts

SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-this-secret")
os.makedirs("uploads", exist_ok=True)


def sign_session(user_id: int) -> str:
    payload = str(user_id).encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"),
                         payload, hashlib.sha256).digest()
    payload_b64 = base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{payload_b64}.{sig_b64}"


def verify_session(token: str) -> int:
    payload_b64, sig_b64 = token.split(".", 1)
    payload = base64.urlsafe_b64decode(
        payload_b64 + "=" * (-len(payload_b64) % 4))
    signature = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
    expected = hmac.new(SECRET_KEY.encode("utf-8"),
                        payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid session token")
    return int(payload.decode("utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(title="Media Feed App", lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.on_event("startup")
async def startup_event() -> None:
    os.makedirs("uploads", exist_ok=True)
    await create_db_and_tables()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> User:
    await create_db_and_tables()
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = verify_session(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def render_dashboard(user_email: str, items: list[dict]) -> str:
    card_html = "".join(
        f"""
        <div class="card">
          <div class="meta">{item['file_type']}</div>
          <h3>{item['caption'] or 'Untitled post'}</h3>
          <p>{item['content'] or ''}</p>
          {f'<img src="{item["url"]}" alt="{item["caption"]}" />' if item['file_type'] and item['file_type'].startswith('image/') else f'<video controls src="{item["url"]}"></video>' if item['url'] else ''}
          <div class="meta">{item['file_name']}</div>
        </div>
        """
        for item in items
    )

    return f"""
    <!doctype html>
    <html>
      <head>
        <title>Media Feed</title>
        <style>
          body {{ font-family: Arial, sans-serif; background: #f4f7fb; margin: 0; padding: 24px; }}
          .wrap {{ max-width: 980px; margin: auto; }}
          .top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }}
          .card {{ background: white; border-radius: 14px; padding: 18px; box-shadow: 0 10px 20px rgba(0,0,0,0.05); }}
          .card img, .card video {{ width: 100%; max-height: 280px; object-fit: cover; border-radius: 10px; margin-top: 12px; }}
          form {{ background: white; padding: 20px; border-radius: 14px; box-shadow: 0 10px 20px rgba(0,0,0,0.05); margin-bottom: 24px; }}
          input, textarea, button {{ width: 100%; box-sizing: border-box; margin-top: 8px; padding: 10px 12px; border-radius: 8px; border: 1px solid #dfe7f5; }}
          button {{ background: #2f6fed; color: white; border: none; cursor: pointer; }}
          .logout {{ width: auto; padding: 10px 18px; background: #111827; }}
          .meta {{ color: #64748b; font-size: 12px; margin-bottom: 10px; }}
          h1 {{ margin: 0; }}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="top">
            <h1>Welcome, {user_email}</h1>
            <form method="post" action="/logout">
              <button class="logout" type="submit">Logout</button>
            </form>
          </div>

          <form method="post" action="/upload" enctype="multipart/form-data">
            <h2>Upload photo or video</h2>
            <input type="file" name="file" required />
            <input type="text" name="caption" placeholder="Caption" />
            <textarea name="content" rows="4" placeholder="Description"></textarea>
            <button type="submit">Upload</button>
          </form>

          <div class="grid">
            {card_html or '<div class="card"><p>No posts yet.</p></div>'}
          </div>
        </div>
      </body>
    </html>
    """


async def save_local_file(file: UploadFile) -> str:
    os.makedirs("uploads", exist_ok=True)
    ext = os.path.splitext(file.filename or "upload.bin")[1] or ".bin"
    file_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join("uploads", file_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return f"/uploads/{file_name}"


async def upload_to_imagekit(file: UploadFile) -> str | None:
    private_key = os.getenv("IMAGEKIT_PRIVATE_KEY")
    public_key = os.getenv("IMAGEKIT_PUBLIC_KEY")
    url_endpoint = os.getenv("IMAGEKIT_URL_ENDPOINT")

    if not (private_key and public_key and url_endpoint):
        return None

    try:
        from imagekitio import ImageKit

        imagekit = ImageKit(
            private_key=private_key,
            public_key=public_key,
            url_endpoint=url_endpoint,
        )

        upload_result = imagekit.upload_file(
            file=file.file,
            file_name=file.filename or "upload.bin",
            options={"folder": "/fast-feed"},
        )

        if isinstance(upload_result, dict):
            return upload_result.get("url") or upload_result.get("response", {}).get("url")
        if hasattr(upload_result, "url"):
            return upload_result.url
    except Exception:
        return None

    return None


@app.get("/")
async def auth_page():
    return HTMLResponse(
        """
        <!doctype html>
        <html>
          <head>
            <title>Login</title>
            <style>
              body { font-family: Arial, sans-serif; background: #f4f7fb; display: grid; place-items: center; height: 100vh; }
              .panel { background: white; width: min(420px, 90vw); padding: 32px; border-radius: 18px; box-shadow: 0 12px 24px rgba(0,0,0,0.06); }
              input, button { width: 100%; box-sizing: border-box; padding: 12px; margin-top: 12px; border-radius: 10px; border: 1px solid #dfe7f5; }
              button { background: #2f6fed; color: white; border: none; cursor: pointer; }
              a { display: block; margin-top: 12px; color: #2f6fed; text-align: center; }
            </style>
          </head>
          <body>
            <div class="panel">
              <h2>Login</h2>
              <form method="post" action="/login">
                <input type="email" name="email" placeholder="Email" required />
                <input type="password" name="password" placeholder="Password" required />
                <button type="submit">Login</button>
              </form>
              <a href="/register-page">Create account</a>
            </div>
          </body>
        </html>
        """
    )


@app.get("/register-page")
async def register_page():
    return HTMLResponse(
        """
        <!doctype html>
        <html>
          <head>
            <title>Register</title>
            <style>
              body { font-family: Arial, sans-serif; background: #f4f7fb; display: grid; place-items: center; height: 100vh; }
              .panel { background: white; width: min(420px, 90vw); padding: 32px; border-radius: 18px; box-shadow: 0 12px 24px rgba(0,0,0,0.06); }
              input, button { width: 100%; box-sizing: border-box; padding: 12px; margin-top: 12px; border-radius: 10px; border: 1px solid #dfe7f5; }
              button { background: #2f6fed; color: white; border: none; cursor: pointer; }
              a { display: block; margin-top: 12px; color: #2f6fed; text-align: center; }
            </style>
          </head>
          <body>
            <div class="panel">
              <h2>Create account</h2>
              <form method="post" action="/register">
                <input type="email" name="email" placeholder="Email" required />
                <input type="password" name="password" placeholder="Password" required />
                <button type="submit">Register</button>
              </form>
              <a href="/">Already have an account?</a>
            </div>
          </body>
        </html>
        """
    )


@app.post("/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    await create_db_and_tables()
    existing = await session.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(email=email.lower(), password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return RedirectResponse(url="/", status_code=303)


@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    await create_db_and_tables()
    user_result = await session.execute(select(User).where(User.email == email.lower()))
    user = user_result.scalar_one_or_none()
    if not user or user.password_hash != hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = sign_session(user.id)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session", value=token,
                        httponly=True, samesite="lax")
    return response


@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session")
    return response


@app.get("/dashboard")
async def dashboard(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await create_db_and_tables()
    result = await session.execute(select(posts).order_by(posts.created_at.desc()))
    items = result.scalars().all()
    payload = [
        {
            "id": post.id,
            "caption": post.caption,
            "content": post.content,
            "url": post.url,
            "file_name": post.file_name,
            "file_type": post.file_type,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
        for post in items
    ]
    return HTMLResponse(render_dashboard(user.email, payload))


@app.post("/upload")
async def upload_post(
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    content: str = Form(default=""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await create_db_and_tables()
    uploaded_url = await upload_to_imagekit(file)
    if uploaded_url is None:
        uploaded_url = await save_local_file(file)

    new_post = posts(
        caption=caption,
        content=content,
        url=uploaded_url,
        file_name=file.filename,
        file_type=file.content_type,
    )

    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/api/feed")
async def api_feed(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    await create_db_and_tables()
    result = await session.execute(select(posts).order_by(posts.created_at.desc()))
    feed_posts = result.scalars().all()

    return [
        {
            "id": post.id,
            "caption": post.caption,
            "content": post.content,
            "url": post.url,
            "file_name": post.file_name,
            "file_type": post.file_type,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
        for post in feed_posts
    ]


@app.post("/api/posts")
async def api_create_post(
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    content: str = Form(default=""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    await create_db_and_tables()
    uploaded_url = await upload_to_imagekit(file)
    if uploaded_url is None:
        uploaded_url = await save_local_file(file)
    post = posts(
        caption=caption,
        content=content,
        url=uploaded_url,
        file_name=file.filename,
        file_type=file.content_type,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return {
        "id": post.id,
        "caption": post.caption,
        "content": post.content,
        "url": post.url,
        "file_name": post.file_name,
        "file_type": post.file_type,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }
