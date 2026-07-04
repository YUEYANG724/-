from PIL import Image, ImageDraw, ImageFont
import os

base = "C:/Users/28471/Documents/柚子之家/photos"
cats = ["婚纱照","个人写真","全家福","儿童摄影","旅拍"]
colors = ["#F4A7B9","#A8D8EA","#F5D6A8","#C9E4C5","#C5B4E3"]
fnt = ImageFont.load_default()
for cat,clr in zip(cats,colors):
    cd = os.path.join(base,cat)
    for i in range(1,4):
        im = Image.new("RGB",(800,600),clr)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([40,40,760,560],radius=16,fill=None,outline="white",width=3)
        d.text((400,260),f"{cat}\n\n照片{i}",fill="white",font=fnt,anchor="mm")
        im.save(os.path.join(cd,f"{i}.jpg"),quality=90)
        print(f"Created {cat}/{i}.jpg")
print("Done!")
