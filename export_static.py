import os
import shutil

import app


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLISH_DIR = os.path.join(BASE_DIR, "docs")
CUSTOM_DOMAIN = "www.youzizhijia.dpdns.org"


def safe_clear_publish_dir():
    publish_real = os.path.realpath(PUBLISH_DIR)
    base_real = os.path.realpath(BASE_DIR)
    if publish_real == base_real or not publish_real.startswith(base_real + os.sep):
        raise RuntimeError("发布目录不安全，已停止导出")
    if os.path.exists(PUBLISH_DIR):
        shutil.rmtree(PUBLISH_DIR)
    os.makedirs(PUBLISH_DIR, exist_ok=True)


def copy_tree_if_exists(source, target):
    if os.path.exists(source):
        shutil.copytree(source, target, dirs_exist_ok=True)


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def export_static_site():
    app.ensure_photos_dir()
    app.ensure_uploads_dir()
    safe_clear_publish_dir()

    write_text(os.path.join(PUBLISH_DIR, "index.html"), app.render_index())
    write_text(os.path.join(PUBLISH_DIR, "api", "categories"), app.json_bytes(app.all_photos_by_category()).decode("utf-8"))
    write_text(os.path.join(PUBLISH_DIR, "api", "categories.json"), app.json_bytes(app.all_photos_by_category()).decode("utf-8"))
    write_text(os.path.join(PUBLISH_DIR, "CNAME"), CUSTOM_DOMAIN + "\n")

    copy_tree_if_exists(app.STATIC_DIR, os.path.join(PUBLISH_DIR, "static"))
    copy_tree_if_exists(app.PHOTOS_DIR, os.path.join(PUBLISH_DIR, "photos"))

    write_text(
        os.path.join(PUBLISH_DIR, "_headers"),
        """/api/categories
  Content-Type: application/json; charset=utf-8
/api/categories.json
  Content-Type: application/json; charset=utf-8
/*
  X-Content-Type-Options: nosniff
""",
    )
    write_text(
        os.path.join(PUBLISH_DIR, "README.txt"),
        "这是柚子摄影客户相册的 GitHub Pages 静态发布目录。GitHub Pages 请设置为 main 分支 /docs 文件夹。\n",
    )

    photo_count = sum(len(photos) for photos in app.all_photos_by_category().values())
    return {
        "publishDir": PUBLISH_DIR,
        "categories": len(app.get_categories()),
        "photos": photo_count,
    }


if __name__ == "__main__":
    result = export_static_site()
    print("Static album exported")
    print(f"Directory: {result['publishDir']}")
    print(f"Categories: {result['categories']}")
    print(f"Photos: {result['photos']}")
