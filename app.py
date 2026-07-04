import base64
import cgi
import json
import mimetypes
import os
import posixpath
import re
import secrets
import shutil
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(STATIC_DIR, "uploads")

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
BACKGROUND_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
BACKGROUND_BASENAME = "header_background"
DEFAULT_LOCAL_URL = "http://127.0.0.1:5000/"
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
LOCAL_ADMIN_HOSTS = {"localhost", "127.0.0.1", "::1", "youzizhijia.local"}


def ensure_photos_dir():
    os.makedirs(PHOTOS_DIR, exist_ok=True)


def ensure_uploads_dir():
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def normalize_base_url(url):
    url = (url or "").strip()
    if not url:
        return DEFAULT_LOCAL_URL
    return url.rstrip("/") + "/"


def public_base_url(handler=None):
    if PUBLIC_BASE_URL:
        return normalize_base_url(PUBLIC_BASE_URL)
    if handler:
        host = handler.headers.get("Host") or "127.0.0.1:5000"
        return normalize_base_url(f"http://{host}/")
    return DEFAULT_LOCAL_URL


def validate_category_name(name):
    name = (name or "").strip()
    forbidden = '<>:"/\\|?*'
    if not name:
        return False, "分类名不能为空"
    if name in {".", ".."}:
        return False, "分类名不合法"
    if any(c in name for c in forbidden):
        return False, "分类名包含非法字符"
    return True, ""


def validate_photo_filename(filename):
    filename = (filename or "").strip()
    if not filename or filename != os.path.basename(filename):
        return False
    return os.path.splitext(filename)[1].lower() in PHOTO_EXTENSIONS


def validate_background_filename(filename):
    filename = (filename or "").strip()
    if not filename or filename != os.path.basename(filename):
        return False
    return os.path.splitext(filename)[1].lower() in BACKGROUND_EXTENSIONS


def safe_category_path(category):
    ok, _ = validate_category_name(category)
    if not ok:
        return None
    ensure_photos_dir()
    root = os.path.realpath(PHOTOS_DIR)
    path = os.path.realpath(os.path.join(PHOTOS_DIR, category))
    if path != root and path.startswith(root + os.sep):
        return path
    return None


def get_categories():
    ensure_photos_dir()
    categories = []
    for name in os.listdir(PHOTOS_DIR):
        path = safe_category_path(name)
        if path and os.path.isdir(path):
            categories.append(name)
    return sorted(categories)


def photo_url(category, filename):
    return f"/photos/{quote(category)}/{quote(filename)}"


def get_photos(category):
    cat_path = safe_category_path(category)
    if not cat_path or not os.path.isdir(cat_path):
        return []

    photos = []
    for filename in sorted(os.listdir(cat_path)):
        if validate_photo_filename(filename):
            photos.append(
                {
                    "filename": filename,
                    "url": photo_url(category, filename),
                    "category": category,
                }
            )
    return photos


def all_photos_by_category():
    return {cat: get_photos(cat) for cat in get_categories()}


def get_header_background_url():
    ensure_uploads_dir()
    for ext in sorted(BACKGROUND_EXTENSIONS):
        filename = BACKGROUND_BASENAME + ext
        path = os.path.join(UPLOADS_DIR, filename)
        if os.path.isfile(path):
            version = int(os.path.getmtime(path))
            return f"/static/uploads/{filename}?v={version}"
    return ""


def get_header_background_style():
    url = get_header_background_url()
    if not url:
        return ""
    return f'--header-bg-image: url("{url}");'


def delete_old_header_backgrounds():
    ensure_uploads_dir()
    for ext in BACKGROUND_EXTENSIONS:
        path = os.path.join(UPLOADS_DIR, BACKGROUND_BASENAME + ext)
        if os.path.isfile(path):
            os.remove(path)


def json_bytes(data):
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def qr_image_url(url):
    data = quote(url, safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=480x480&margin=16&data={data}"


def read_template(name):
    with open(os.path.join(TEMPLATES_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def replace_url_for(html):
    replacements = {
        "{{ url_for('static', filename='css/style.css') }}": "/static/css/style.css",
        '{{ url_for("static", filename="css/style.css") }}': "/static/css/style.css",
        "{{ url_for('static', filename='js/gallery.js') }}": "/static/js/gallery.js",
        '{{ url_for("static", filename="js/gallery.js") }}': "/static/js/gallery.js",
        "{{ url_for('index') }}": "/",
        "{{ url_for('admin_page') }}": "/admin",
        "{{ url_for('qrcode_page') }}": "/qrcode",
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    return html


def render_index():
    html = replace_url_for(read_template("index.html"))
    html = html.replace("{{ header_background_url }}", get_header_background_url())
    html = html.replace("{{ header_background_style }}", get_header_background_style())
    buttons = "\n".join(
        f'    <button class="category-btn" data-category="{cat}">{cat}</button>'
        for cat in get_categories()
    )
    return re.sub(
        r"\s*\{% for category in categories %\}.*?\{% endfor %\}",
        "\n" + buttons,
        html,
        flags=re.S,
    )


def render_admin():
    html = replace_url_for(read_template("admin.html"))
    html = html.replace("{{ header_background_url }}", get_header_background_url())
    html = html.replace("{{ header_background_style }}", get_header_background_style())
    options = "\n".join(f'          <option value="{cat}">{cat}</option>' for cat in get_categories())
    return re.sub(
        r"\s*\{% for cat in categories %\}.*?\{% endfor %\}",
        "\n" + options,
        html,
        flags=re.S,
    )


def render_qrcode(handler):
    html = replace_url_for(read_template("qrcode.html"))
    html = html.replace("{{ header_background_url }}", get_header_background_url())
    html = html.replace("{{ header_background_style }}", get_header_background_style())
    return html.replace("{{ public_url }}", public_base_url(handler))


class PhotoAlbumHandler(SimpleHTTPRequestHandler):
    server_version = "YouziPhotoAlbum/1.0"

    def log_message(self, fmt, *args):
        try:
            print(f"{self.address_string()} - {fmt % args}")
        except Exception:
            pass

    def send_bytes(self, data, content_type="text/plain; charset=utf-8", status=HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, data, status=HTTPStatus.OK):
        self.send_bytes(json_bytes(data), "application/json; charset=utf-8", status)

    def send_html(self, html, status=HTTPStatus.OK):
        self.send_bytes(html.encode("utf-8"), "text/html; charset=utf-8", status)

    def send_not_found(self):
        self.send_bytes(b"Not found", "text/plain; charset=utf-8", HTTPStatus.NOT_FOUND)

    def path_parts(self):
        parsed = urlparse(self.path)
        path = posixpath.normpath(parsed.path)
        return [unquote(p) for p in path.split("/") if p]

    def admin_host_is_local(self):
        host = (self.headers.get("Host") or "").split(":")[0].strip("[]").lower()
        return host in LOCAL_ADMIN_HOSTS

    def admin_authenticated(self):
        if not ADMIN_PASSWORD:
            return self.admin_host_is_local()

        auth = self.headers.get("Authorization", "")
        if not auth.lower().startswith("basic "):
            return False
        try:
            raw = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
            _, password = raw.split(":", 1)
        except Exception:
            return False
        return secrets.compare_digest(password, ADMIN_PASSWORD)

    def require_admin(self):
        if self.admin_authenticated():
            return True

        if urlparse(self.path).path.startswith("/api/"):
            self.send_json({"success": False, "error": "需要后台密码"}, HTTPStatus.UNAUTHORIZED)
        else:
            body = "需要后台密码。请在本机访问后台，或设置 ADMIN_PASSWORD 后输入密码。"
            data = body.encode("utf-8")
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("WWW-Authenticate", 'Basic realm="Youzi Photo Admin"')
            self.end_headers()
            self.wfile.write(data)
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/":
            self.send_html(render_index())
            return
        if route == "/api/categories":
            self.send_json(all_photos_by_category())
            return
        if route == "/api/qrcode":
            if not self.require_admin():
                return
            url = public_base_url(self)
            self.send_json({"qr": qr_image_url(url), "url": url})
            return
        if route == "/qr.png":
            if not self.require_admin():
                return
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", qr_image_url(public_base_url(self)))
            self.end_headers()
            return
        if route == "/qrcode":
            if not self.require_admin():
                return
            self.send_html(render_qrcode(self))
            return
        if route == "/admin":
            if not self.require_admin():
                return
            self.send_html(render_admin())
            return
        if route == "/api/admin/categories":
            if not self.require_admin():
                return
            self.send_json(all_photos_by_category())
            return
        if route == "/api/admin/settings":
            if not self.require_admin():
                return
            self.send_json({"headerBackgroundUrl": get_header_background_url()})
            return
        if route.startswith("/static/"):
            self.serve_static(route)
            return
        if route.startswith("/photos/"):
            self.serve_photo()
            return

        self.send_not_found()

    def serve_static(self, route):
        relative = unquote(route[len("/static/") :])
        full_path = os.path.realpath(os.path.join(STATIC_DIR, relative))
        root = os.path.realpath(STATIC_DIR)
        if not full_path.startswith(root + os.sep) or not os.path.isfile(full_path):
            self.send_not_found()
            return
        content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        with open(full_path, "rb") as f:
            self.send_bytes(f.read(), content_type)

    def serve_photo(self):
        parts = self.path_parts()
        if len(parts) != 3:
            self.send_not_found()
            return
        _, category, filename = parts
        cat_path = safe_category_path(category)
        if not cat_path or not os.path.isdir(cat_path) or not validate_photo_filename(filename):
            self.send_not_found()
            return
        full_path = os.path.realpath(os.path.join(cat_path, filename))
        if not full_path.startswith(os.path.realpath(cat_path) + os.sep) or not os.path.isfile(full_path):
            self.send_not_found()
            return
        content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
        with open(full_path, "rb") as f:
            self.send_bytes(f.read(), content_type)

    def do_POST(self):
        if not self.require_admin():
            return

        route = urlparse(self.path).path
        if route == "/api/admin/category/create":
            self.create_category()
        elif route == "/api/admin/category/rename":
            self.rename_category()
        elif route == "/api/admin/category/delete":
            self.delete_category()
        elif route == "/api/admin/photo/delete":
            self.delete_photo()
        elif route == "/api/admin/upload":
            self.upload_photos()
        elif route == "/api/admin/background":
            self.upload_background()
        elif route == "/api/admin/export-static":
            self.export_static()
        else:
            self.send_not_found()

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}

    def create_category(self):
        data = self.read_json_body()
        name = (data.get("name") or "").strip()
        ok, error = validate_category_name(name)
        if not ok:
            self.send_json({"success": False, "error": error})
            return
        cat_path = safe_category_path(name)
        if os.path.exists(cat_path):
            self.send_json({"success": False, "error": f"分类「{name}」已存在"})
            return
        os.makedirs(cat_path)
        self.send_json({"success": True, "category": name})

    def rename_category(self):
        data = self.read_json_body()
        old = (data.get("old") or "").strip()
        new = (data.get("new") or "").strip()
        old_ok, old_error = validate_category_name(old)
        new_ok, new_error = validate_category_name(new)
        if not old_ok or not new_ok:
            self.send_json({"success": False, "error": old_error or new_error})
            return

        old_path = safe_category_path(old)
        new_path = safe_category_path(new)
        if not os.path.isdir(old_path):
            self.send_json({"success": False, "error": f"分类「{old}」不存在"})
            return
        if os.path.exists(new_path):
            self.send_json({"success": False, "error": f"分类「{new}」已存在"})
            return
        os.rename(old_path, new_path)
        self.send_json({"success": True, "old": old, "new": new})

    def delete_category(self):
        data = self.read_json_body()
        name = (data.get("name") or "").strip()
        ok, error = validate_category_name(name)
        if not ok:
            self.send_json({"success": False, "error": error})
            return
        cat_path = safe_category_path(name)
        if not os.path.isdir(cat_path):
            self.send_json({"success": False, "error": f"分类「{name}」不存在"})
            return
        shutil.rmtree(cat_path)
        self.send_json({"success": True})

    def delete_photo(self):
        data = self.read_json_body()
        category = (data.get("category") or "").strip()
        filename = (data.get("filename") or "").strip()
        cat_path = safe_category_path(category)
        if not cat_path or not os.path.isdir(cat_path) or not validate_photo_filename(filename):
            self.send_json({"success": False, "error": "参数不完整"})
            return
        full_path = os.path.realpath(os.path.join(cat_path, filename))
        if not full_path.startswith(os.path.realpath(cat_path) + os.sep) or not os.path.isfile(full_path):
            self.send_json({"success": False, "error": "文件不存在"})
            return
        os.remove(full_path)
        self.send_json({"success": True})

    def upload_photos(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        category = (form.getvalue("category") or "").strip()
        cat_path = safe_category_path(category)
        if not cat_path or not os.path.isdir(cat_path):
            self.send_json({"success": False, "error": f"分类「{category}」不存在"})
            return

        files = form["photos"] if "photos" in form else []
        if not isinstance(files, list):
            files = [files]

        uploaded = []
        errors = []
        for item in files:
            if not getattr(item, "filename", ""):
                continue
            original_name = os.path.basename(item.filename)
            if not validate_photo_filename(original_name):
                errors.append(f"{original_name} 格式不支持")
                continue
            safe_name = original_name
            save_path = os.path.join(cat_path, safe_name)
            if os.path.exists(save_path):
                base, ext = os.path.splitext(safe_name)
                safe_name = f"{base}_{int(time.time())}{ext}"
                save_path = os.path.join(cat_path, safe_name)
            with open(save_path, "wb") as f:
                shutil.copyfileobj(item.file, f)
            uploaded.append(safe_name)

        if not uploaded and not errors:
            self.send_json({"success": False, "error": "请选择要上传的照片"})
            return
        self.send_json({"success": True, "uploaded": uploaded, "errors": errors, "category": category})

    def upload_background(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type"),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        item = form["background"] if "background" in form else None
        if isinstance(item, list):
            item = item[0] if item else None
        if item is None or not getattr(item, "filename", ""):
            self.send_json({"success": False, "error": "请选择背景图片"})
            return

        original_name = os.path.basename(item.filename)
        if not validate_background_filename(original_name):
            self.send_json({"success": False, "error": "背景图仅支持 JPG / PNG / WebP"})
            return

        ensure_uploads_dir()
        delete_old_header_backgrounds()
        ext = os.path.splitext(original_name)[1].lower()
        save_path = os.path.join(UPLOADS_DIR, BACKGROUND_BASENAME + ext)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(item.file, f)

        self.send_json({"success": True, "url": get_header_background_url()})

    def export_static(self):
        try:
            import export_static

            result = export_static.export_static_site()
            self.send_json({"success": True, **result})
        except Exception as exc:
            self.send_json({"success": False, "error": f"生成失败：{exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main():
    ensure_photos_dir()
    ensure_uploads_dir()
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "5000"))
    httpd = ThreadingHTTPServer((host, port), PhotoAlbumHandler)
    try:
        print(f"柚子摄影相册已启动: http://127.0.0.1:{port}/")
        print(f"后台管理: http://127.0.0.1:{port}/admin")
        print(f"二维码: http://127.0.0.1:{port}/qrcode")
    except Exception:
        pass
    httpd.serve_forever()


if __name__ == "__main__":
    main()
