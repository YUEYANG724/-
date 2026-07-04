# 柚子摄影客户相册

这是一个给摄影店使用的微信扫码相册：

- 客户访问 `/` 查看相册
- 照片按 `photos/分类名/照片文件` 自动分类展示
- 店主访问 `/admin` 上传照片、创建分类、删除照片
- 店主访问 `/admin` 的“封面背景”上传首页顶部背景图
- 店主访问 `/qrcode` 生成固定客户访问二维码

## 启动

```powershell
python app.py
```

如果你的电脑没有把 Python 加到 PATH，可以用 Codex 自带 Python 启动：

```powershell
& "C:\Users\28471\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py
```

本机打开：

- 相册：http://127.0.0.1:5000/
- 后台：http://127.0.0.1:5000/admin
- 二维码：http://127.0.0.1:5000/qrcode

这台电脑也可以直接双击 `start_album.bat` 一键启动。

## 放照片

把照片放到 `photos` 目录下对应分类即可，例如：

```text
photos/
  婚纱照/
    001.jpg
    002.jpg
  全家福/
    001.jpg
```

也可以在后台新建分类并上传照片。

## 更换首页顶部背景

打开后台：

```text
http://127.0.0.1:5000/admin
```

点击“封面背景”，选择一张横向图片上传即可。建议使用横图，格式支持 `JPG / PNG / WebP`。

## 接外网

客户在店外扫码，需要一个公网可访问地址。可以使用：

- 云服务器 + 域名
- 宝塔 / Nginx / IIS 反向代理
- 内网穿透服务，例如 ngrok、cpolar、花生壳

拿到公网地址后，启动前设置固定二维码地址：

```powershell
$env:PUBLIC_BASE_URL="https://你的公网域名或穿透地址"
python app.py
```

如果公网开放后台，请同时设置后台密码：

```powershell
$env:PUBLIC_BASE_URL="https://你的公网域名或穿透地址"
$env:ADMIN_PASSWORD="换成一个强密码"
python app.py
```

设置后访问 `/qrcode` 下载二维码。二维码会固定指向 `PUBLIC_BASE_URL`，以后只要这个公网地址不变，二维码就不用重新发。

二维码图片由公开二维码图片服务生成；如果你希望完全离线生成二维码，可以之后再换成服务器端二维码库。

## 安全提醒

- 不要把 `/admin` 发给客户。
- 没有设置 `ADMIN_PASSWORD` 时，后台默认只允许本机地址访问。
- 真正长期对外使用，建议使用 HTTPS 域名。
