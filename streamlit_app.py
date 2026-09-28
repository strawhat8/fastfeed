import asyncio
import hashlib
import os
import uuid
from pathlib import Path

import streamlit as st
from sqlalchemy import select

from app.database import User, async_sessionmaker, create_db_and_tables, posts

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="FastFeed", page_icon="✨", layout="wide")


async def get_user_by_email(email: str):
    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()


async def create_user(email: str, password: str):
    async with async_sessionmaker() as session:
        existing = await session.execute(select(User).where(User.email == email.lower()))
        if existing.scalar_one_or_none():
            return False

        user = User(email=email.lower(), password_hash=hash_password(password))
        session.add(user)
        await session.commit()
        return True


async def login_user(email: str, password: str):
    async with async_sessionmaker() as session:
        result = await session.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            return None
        if user.password_hash != hash_password(password):
            return None
        return user.id


async def save_post_to_db(caption: str, content: str, url: str | None, file_name: str | None, file_type: str | None):
    async with async_sessionmaker() as session:
        post = posts(
            caption=caption,
            content=content,
            url=url,
            file_name=file_name,
            file_type=file_type,
        )
        session.add(post)
        await session.commit()
        await session.refresh(post)
        return post


async def fetch_posts():
    async with async_sessionmaker() as session:
        result = await session.execute(select(posts).order_by(posts.created_at.desc()))
        return result.scalars().all()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def save_local_upload(uploaded_file):
    ext = Path(uploaded_file.name).suffix or ".bin"
    file_name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / file_name
    with path.open("wb") as f:
        f.write(uploaded_file.getvalue())
    return f"/uploads/{file_name}", str(path)


def normalize_media_source(value):
    if value is None:
        return None

    if isinstance(value, (bytes, bytearray)):
        return bytes(value)

    if hasattr(value, "getvalue"):
        try:
            raw = value.getvalue()
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw)
        except Exception:
            pass

    if hasattr(value, "read"):
        try:
            raw = value.read()
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw)
        except Exception:
            pass

    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None
    return value


def safe_render_image(media_source):
    if media_source is None:
        return False

    try:
        if isinstance(media_source, (bytes, bytearray)):
            st.image(bytes(media_source), width=400)
            return True

        if isinstance(media_source, str):
            local_path = media_source.lstrip("/")
            if media_source.startswith(("http://", "https://")):
                st.image(media_source, width=400)
                return True
            if os.path.exists(local_path):
                st.image(local_path, width=400)
                return True
            st.markdown(f"[Open file]({media_source})")
            return False

    except Exception:
        st.caption("Preview unavailable — this image could not be decoded.")
        if isinstance(media_source, str):
            st.markdown(f"[Open file]({media_source})")
        return False

    return False


def safe_render_video(media_source):
    if media_source is None:
        return False

    try:
        if isinstance(media_source, str):
            if media_source.startswith(("http://", "https://")):
                st.video(media_source)
                return True
            local_path = media_source.lstrip("/")
            if os.path.exists(local_path):
                st.video(local_path)
                return True
            st.markdown(f"[Open file]({media_source})")
            return False
    except Exception:
        st.caption("Preview unavailable — this video could not be decoded.")
        if isinstance(media_source, str):
            st.markdown(f"[Open file]({media_source})")
        return False

    return False


async def ensure_db():
    await create_db_and_tables()


asyncio.run(ensure_db())

if "theme" not in st.session_state:
    st.session_state.theme = "dark"


def render_theme_css():
    if st.session_state.theme == "dark":
        return """
        <style>
            .stApp {
                background: #0f0f0f;
                color: #f5f7fb;
            }
            div[data-testid="stSidebar"] {
                background: rgba(18, 18, 18, 0.9);
                border-right: 1px solid rgba(255,255,255,0.06);
            }
            .block-container {
                padding-top: 1rem;
                padding-bottom: 3rem;
                max-width: 1600px !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
            .stButton > button {
                background: linear-gradient(90deg, #ff0033, #ff6a00);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0.75rem 1.1rem;
                font-weight: 700;
                box-shadow: 0 8px 18px rgba(255, 57, 57, 0.35);
            }
            .stTextInput > div > div > input,
            .stFileUploader > div,
            .stTextarea > div > div > textarea {
                background: rgba(30, 30, 30, 0.82);
                color: white;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 14px;
            }
            .feed-shell {
                max-width: 1500px;
                margin: 0 auto;
            }
            .feed-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
                gap: 1.25rem;
                align-items: start;
            }
            .feed-card {
                background: rgba(22, 22, 22, 0.9);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 22px;
                overflow: hidden;
                padding: 0;
                box-shadow: 0 18px 40px rgba(0,0,0,0.2);
            }
            .feed-card .media-wrap {
                border-radius: 16px 16px 0 0;
                overflow: hidden;
                background: #111;
            }
            .meta-row {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                padding: 0.85rem 1rem 0.2rem 1rem;
            }
            .avatar {
                width: 2.1rem;
                height: 2.1rem;
                border-radius: 50%;
                background: linear-gradient(135deg, #ff0033, #ff6a00);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.75rem;
                font-weight: 800;
            }
            .meta-copy {
                flex: 1;
                min-width: 0;
            }
            .channel-name {
                color: #f5f7fb;
                font-weight: 700;
                font-size: 0.8rem;
                line-height: 1.2;
            }
            .meta-sub {
                color: #9ca3af;
                font-size: 0.72rem;
            }
            .post-title {
                padding: 0.35rem 1rem 0;
                color: #f8fafc;
                font-size: 1.05rem;
                line-height: 1.35;
                font-weight: 700;
            }
            .post-body {
                padding: 0.35rem 1rem 0.9rem;
                color: #d1d5db;
                font-size: 0.88rem;
                line-height: 1.5;
            }
            .meta-footer {
                padding: 0 1rem 1rem;
                color: #9ca3af;
                font-size: 0.72rem;
            }
            .sidebar-box {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 14px;
                padding: 0.7rem 0.8rem;
                margin: 0.6rem 0;
            }
            .auth-shell {
                max-width: 530px;
                margin: 4rem auto 0 auto;
                padding-top: 0.5rem;
            }
            .auth-card {
                background: rgba(17,17,17,0.88);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 22px;
                padding: 1.5rem;
                box-shadow: 0 20px 50px rgba(0,0,0,0.28);
            }
            .auth-brand {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.8rem;
                margin-bottom: 1.5rem;
                text-align: center;
            }
            .nav-section {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }
            .nav-section button {
                width: 100%;
                text-align: left;
                justify-content: flex-start;
                border-radius: 12px;
                padding: 0.8rem 0.9rem;
                border: 1px solid rgba(255,255,255,0.08);
                background: rgba(255,255,255,0.02);
                color: #f5f7fb;
                font-weight: 700;
            }
            .nav-section button:hover {
                border-color: rgba(255,255,255,0.16);
                background: rgba(255,255,255,0.04);
            }
            .brand-mark {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 42px;
                height: 42px;
                border-radius: 12px;
                background: linear-gradient(135deg, #ff0033, #ff6a00);
                color: white;
                font-size: 1.2rem;
                font-weight: 800;
                box-shadow: 0 8px 18px rgba(255, 57, 57, 0.35);
            }
            .brand-title {
                font-size: 2.1rem;
                font-weight: 900;
                letter-spacing: -0.04em;
                margin: 0.2rem 0 0.2rem 0;
            }
            .theme-toggle {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(255,255,255,0.08);
                background: rgba(255,255,255,0.04);
                color: white;
                border-radius: 999px;
                padding: 0.55rem 0.9rem;
                font-weight: 700;
                margin-top: 0.5rem;
            }
            h1, h2, h3, h4 {
                color: white !important;
            }
            p, div, label {
                color: #e2e8f0;
            }
        </style>
        """
    return """
        <style>
            .stApp {
                background: #f3f5f9;
                color: #101828;
            }
            div[data-testid="stSidebar"] {
                background: rgba(255, 255, 255, 0.92);
                border-right: 1px solid rgba(15, 23, 42, 0.08);
            }
            .block-container {
                padding-top: 1rem;
                padding-bottom: 3rem;
                max-width: 1600px !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }
            .stButton > button {
                background: linear-gradient(90deg, #ff0033, #ff6a00);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 0.75rem 1.1rem;
                font-weight: 700;
                box-shadow: 0 8px 18px rgba(255, 57, 57, 0.2);
            }
            .stTextInput > div > div > input,
            .stFileUploader > div,
            .stTextarea > div > div > textarea {
                background: rgba(255,255,255,0.9);
                color: #111827;
                border: 1px solid rgba(148,163,184,0.4);
                border-radius: 14px;
            }
            .feed-shell {
                max-width: 1500px;
                margin: 0 auto;
            }
            .feed-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
                gap: 1.25rem;
                align-items: start;
            }
            .feed-card {
                background: rgba(255,255,255,0.95);
                border: 1px solid rgba(15,23,42,0.06);
                border-radius: 22px;
                overflow: hidden;
                padding: 0;
                box-shadow: 0 12px 30px rgba(15,23,42,0.08);
            }
            .feed-card .media-wrap {
                border-radius: 16px 16px 0 0;
                overflow: hidden;
                background: #f1f5f9;
            }
            .meta-row {
                display: flex;
                align-items: center;
                gap: 0.7rem;
                padding: 0.85rem 1rem 0.2rem 1rem;
            }
            .avatar {
                width: 2.1rem;
                height: 2.1rem;
                border-radius: 50%;
                background: linear-gradient(135deg, #ff0033, #ff6a00);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.75rem;
                font-weight: 800;
                color: white;
            }
            .meta-copy {
                flex: 1;
                min-width: 0;
            }
            .channel-name {
                color: #0f172a;
                font-weight: 700;
                font-size: 0.8rem;
                line-height: 1.2;
            }
            .meta-sub {
                color: #475569;
                font-size: 0.72rem;
            }
            .post-title {
                padding: 0.35rem 1rem 0;
                color: #0f172a;
                font-size: 1.05rem;
                line-height: 1.35;
                font-weight: 700;
            }
            .post-body {
                padding: 0.35rem 1rem 0.9rem;
                color: #334155;
                font-size: 0.88rem;
                line-height: 1.5;
            }
            .meta-footer {
                padding: 0 1rem 1rem;
                color: #64748b;
                font-size: 0.72rem;
            }
            .sidebar-box {
                background: rgba(15,23,42,0.03);
                border: 1px solid rgba(15,23,42,0.06);
                border-radius: 14px;
                padding: 0.7rem 0.8rem;
                margin: 0.6rem 0;
            }
            .auth-shell {
                max-width: 530px;
                margin: 4rem auto 0 auto;
                padding-top: 0.5rem;
            }
            .auth-card {
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(15,23,42,0.08);
                border-radius: 22px;
                padding: 1.5rem;
                box-shadow: 0 16px 40px rgba(15,23,42,0.08);
            }
            .auth-brand {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.8rem;
                margin-bottom: 1.5rem;
                text-align: center;
            }
            .nav-section {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                margin-top: 0.75rem;
            }
            .nav-section button {
                width: 100%;
                text-align: left;
                justify-content: flex-start;
                border-radius: 12px;
                padding: 0.8rem 0.9rem;
                border: 1px solid rgba(15,23,42,0.08);
                background: rgba(15,23,42,0.02);
                color: #0f172a;
                font-weight: 700;
            }
            .nav-section button:hover {
                border-color: rgba(15,23,42,0.15);
                background: rgba(15,23,42,0.04);
            }
            .brand-mark {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 42px;
                height: 42px;
                border-radius: 12px;
                background: linear-gradient(135deg, #ff0033, #ff6a00);
                color: white;
                font-size: 1.2rem;
                font-weight: 800;
                box-shadow: 0 8px 18px rgba(255, 57, 57, 0.2);
            }
            .brand-title {
                font-size: 2.1rem;
                font-weight: 900;
                letter-spacing: -0.04em;
                margin: 0.2rem 0 0.2rem 0;
            }
            .theme-toggle {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                border: 1px solid rgba(15,23,42,0.08);
                background: rgba(15,23,42,0.03);
                color: #111827;
                border-radius: 999px;
                padding: 0.55rem 0.9rem;
                font-weight: 700;
                margin-top: 0.5rem;
            }
            h1, h2, h3, h4 {
                color: #0f172a !important;
            }
            p, div, label {
                color: #0f172a;
            }
        </style>
        """


st.markdown(render_theme_css(), unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = None


if st.session_state.user_id is None:
    st.markdown("<div style='height: 38px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="auth-shell">
            <div class="auth-card">
                <div class="auth-brand">
                    <div class="brand-mark">F</div>
                    <div class="brand-title">FastFeed</div>
                </div>
        """,
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Login", "Create account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                user_id = asyncio.run(login_user(email, password))
                if user_id:
                    st.session_state.user_id = user_id
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    with tab_register:
        with st.form("register_form"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input(
                "Password", type="password", key="reg_password")
            submitted = st.form_submit_button("Create account")
            if submitted:
                ok = asyncio.run(create_user(email, password))
                if ok:
                    st.success("Account created. Please log in.")
                else:
                    st.warning("That email already exists.")
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

st.sidebar.title("FastFeed")
st.sidebar.write(f"Signed in as: {st.session_state.user_id}")

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Feed"

st.sidebar.markdown('<div class="nav-section">', unsafe_allow_html=True)
for page_name in ["Feed", "Upload"]:
    if st.sidebar.button(page_name, key=f"nav_{page_name}", use_container_width=True):
        st.session_state.nav_page = page_name
        st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.nav_page = "Feed"
    st.rerun()

if st.session_state.nav_page == "Upload":
    st.markdown('<div class="feed-shell">', unsafe_allow_html=True)
    st.title("Upload")
    st.caption("Share a photo or video with your feed")

    with st.container():
        with st.form("post_form"):
            uploaded_file = st.file_uploader(
                "Upload a photo or video",
                type=["jpg", "jpeg", "png", "gif",
                      "mp4", "mov", "webm", "avi", "m4v"],
            )
            caption = st.text_input("Caption")
            content = st.text_area("Description")
            submitted = st.form_submit_button("Publish")

            if submitted:
                if uploaded_file is None:
                    st.warning("Please select a file first.")
                else:
                    url, _ = save_local_upload(uploaded_file)
                    asyncio.run(save_post_to_db(caption, content,
                                url, uploaded_file.name, uploaded_file.type))
                    st.success("Post published!")
                    st.session_state.nav_page = "Feed"
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="feed-shell">', unsafe_allow_html=True)
st.title("Feed")
st.caption("Fresh media from your own gallery")

posts = asyncio.run(fetch_posts())

if not posts:
    st.info("No posts yet. Upload the first one from the sidebar.")
else:
    st.markdown('<div class="feed-grid">', unsafe_allow_html=True)
    for post in posts:
        st.markdown('<div class="feed-card">', unsafe_allow_html=True)
        media_source = normalize_media_source(post.url)

        if media_source is not None and post.file_type and post.file_type.startswith("image/"):
            st.markdown('<div class="media-wrap">', unsafe_allow_html=True)
            if not safe_render_image(media_source):
                st.caption("No valid preview available for this image.")
            st.markdown('</div>', unsafe_allow_html=True)
        elif media_source is not None and post.file_type and post.file_type.startswith("video/"):
            st.markdown('<div class="media-wrap">', unsafe_allow_html=True)
            if not safe_render_video(media_source):
                st.caption("No valid preview available for this video.")
            st.markdown('</div>', unsafe_allow_html=True)
        elif isinstance(media_source, str) and media_source.lower().endswith((".mp4", ".mov", ".webm", ".avi", ".m4v")):
            st.markdown('<div class="media-wrap">', unsafe_allow_html=True)
            if not safe_render_video(media_source):
                st.caption("No valid preview available for this video.")
            st.markdown('</div>', unsafe_allow_html=True)
        elif isinstance(media_source, str) and media_source:
            st.markdown('<div class="media-wrap">', unsafe_allow_html=True)
            st.markdown(f"[Open file]({media_source})")
            st.markdown('</div>', unsafe_allow_html=True)
        elif media_source is None:
            st.markdown('<div class="media-wrap">', unsafe_allow_html=True)
            st.caption("No media attached")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            """
            <div class="meta-row">
                <div class="avatar">F</div>
                <div class="meta-copy">
                    <div class="channel-name">FastFeed</div>
                    <div class="meta-sub">Uploaded media</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='post-title'>{post.caption or 'Untitled post'}</div>", unsafe_allow_html=True)
        if post.content:
            st.markdown(
                f"<div class='post-body'>{post.content}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='meta-footer'>{post.file_name or 'media'} • {post.created_at.strftime('%Y-%m-%d %H:%M') if post.created_at else ''}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
