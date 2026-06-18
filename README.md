# Live Photo / 实况照片工具
| ↓视频+图片转换 | 换封面的不会改变本来的源数据 |
| --- | --- |
| ![](https://img11.360buyimg.com/cxxjwimg/jfs/t1/448805/17/16641/2185302/00508e02F95e827d9/06d72d0500398965.webp) | ![](https://img11.360buyimg.com/cxxjwimg/jfs/t1/453189/12/14644/3168074/00508e02Fcdba5f18/06d72d0500c307e8.webp) |


这里有两个脚本：`replace_live_photo_cover.py` 用来给已有单文件 Live Photo / 实况照片更换封面，`create_live_photo.py` 用来把一张封面图和一个 MP4 合成为新的单文件 Live Photo / 实况照片。

> 一个小技巧：Ctrl+Shift+C 能直接复制文件的全路径

## 页面版

不想写命令的话，直接双击打开：

```text
D:\Desktop\sk\index.html
```

页面里有两个功能：

- `合成实况照片`：选择封面图和 MP4 视频，生成新的实况照片 JPG。
- `实况照片换封面`：选择已有单文件实况照片 JPG 和新封面图，生成换好封面的 JPG。

所有处理都在浏览器本地完成，不会上传文件。

下面先说明封面替换脚本。

## 更换已有实况照片封面

这个脚本用于替换 Android / 小米 / Google 风格的单文件 Live Photo / 实况照片封面。

适用文件通常长这样：

- `MVIMG_20260613_200721.jpg`
- 文件本身是 `.jpg`
- 图片末尾还嵌入了一段 MP4 动态视频
- 不是 iPhone 那种 `JPG + MOV` 两个文件配对的 Live Photo

脚本会做三件事：

1. 读取原 Live Photo / 实况照片里的元数据。
2. 把你指定的新图片裁切或适配成原照片尺寸。
3. 生成新的 JPG，并把原来的动态视频段原封不动接回去。

## 文件位置

假设。。。脚本路径：

```powershell
D:\Desktop\sk\replace_live_photo_cover.py
```

## 环境要求

需要 Python 3，并安装 Pillow：

```powershell
python -m pip install pillow
```

检查是否安装成功：

```powershell
python -c "from PIL import Image; print('Pillow OK')"
```

## 换封面的基础用法：生成新文件

![](https://img11.360buyimg.com/cxxjwimg/jfs/t1/449235/12/17328/67940/6a3349e9Ff239b88e/06d758f2a76ef672.webp)

推荐先用这种方式，不会覆盖原图。

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg"
```

默认会在原图同目录生成：

```text
D:\Desktop\1\MVIMG_20260613_200721_cover_replaced.jpg
```

你可以先打开这个新文件确认封面和动态效果都正常。

## Demo：指定输出文件名

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --output "D:\Desktop\1\demo_new_cover.jpg"
```

运行完成后打开：

```text
D:\Desktop\1\demo_new_cover.jpg
```

## Demo：直接替换原文件

确认新文件没问题后，可以直接替换原图：

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --replace
```

使用 `--replace` 时，脚本会先自动备份原文件。

备份文件名类似：

```text
MVIMG_20260613_200721.backup_20260616_173500.jpg
```

## 封面适配方式

默认是裁切填满，适合手机照片：

```powershell
--fit crop
```

可选值：

```text
crop     裁切填满，不留黑边，默认推荐
contain  完整显示新封面，可能出现黑边
stretch  强制拉伸到原图尺寸，可能变形
```

示例：

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --fit contain
```

## 调整 JPG 质量

默认质量是 95。

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --quality 98
```

质量越高，文件越大。

## 还原备份

如果用了 `--replace`，想恢复原图，把备份复制回原文件名即可。

示例：

```powershell
Copy-Item `
  -LiteralPath "D:\Desktop\1\MVIMG_20260613_200721.backup_20260616_173500.jpg" `
  -Destination "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  -Force
```

注意把备份文件名换成你实际生成的那个。

## 常见问题

### 1. 提示缺少 Pillow

运行：

```powershell
python -m pip install pillow
```

### 2. 提示没有找到 Live Photo / 实况照片的视频长度元数据 Item:Length

说明这个文件可能不是单文件 Live Photo / 实况照片，或者Live Photo / 实况照片格式不是当前脚本支持的类型。

这个脚本主要支持类似小米 / Google 的 `MVIMG_*.jpg`，也就是 JPG 末尾嵌 MP4 的格式。

### 3. iPhone 的实况照片能不能用？

不能直接用这个脚本。

iPhone Live Photo 通常是 `JPG/HEIC + MOV` 两个文件配对，需要另一种处理方式。

### 4. 为什么有的相册看不到动态效果？

Windows 自带图片查看器通常只显示静态 JPG，不一定识别 Live Photo / 实况照片。

建议用手机相册、Google Photos、支持 Live Photo / 实况照片 的图库 App 测试。

## 本次真实命令

你这次的文件可以这样跑：

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --output "D:\Desktop\1\MVIMG_20260613_200721_cover_replaced.jpg"
```

确认没问题后再覆盖原图：

```powershell
python "D:\Desktop\sk\replace_live_photo_cover.py" `
  --input "D:\Desktop\1\MVIMG_20260613_200721.jpg" `
  --cover "D:\Desktop\1\1.jpg" `
  --replace
```



---





# 从封面图和视频合成 Live Photo / 实况照片

![合成截图](https://zntx.cc/album/upload/956/2026/06/18/1070132_0832110.png)

如果你手里有一张封面图和一个 MP4，也可以用下面这个脚本合成一个单文件 Live Photo / 实况照片 JPG。
> 如果输出png是不会有动态效果的
![](https://img11.360buyimg.com/cxxjwimg/jfs/t1/450953/20/15983/102140/6a33475eFe16e03eb/06d74c52869efcd4.webp)

脚本路径：

```powershell
D:\Desktop\sk\create_live_photo.py
```

它会把：

```text
封面 JPG/PNG/WebP 等图片 + MP4 视频
```

合成为：

```text
一个 .jpg 文件
```

这个 `.jpg` 前半部分是封面图，末尾嵌入 MP4，并带有 Live Photo / 实况照片 XMP 元数据。

注意：运行脚本时建议显式写 `python`。`--output` 可以不填，默认输出到封面图同目录，文件名是 `封面名-实况图.jpg`。

## 合成脚本基础用法

```powershell
python "D:\Desktop\sk\create_live_photo.py" `
  --cover "D:\Desktop\1\1.jpg" `
  --video "D:\Desktop\1\1.mp4"
```

上面的命令会默认生成：

```text
D:\Desktop\1\1-实况图.jpg
```

如果你的封面文件叫 `封面.png`，可以这样运行：

```powershell
python "D:\Desktop\sk\create_live_photo.py" `
  --cover "D:\Desktop\1\封面.png" `
  --video "D:\Desktop\1\1.mp4"
```

会默认生成：

```text
D:\Desktop\1\封面-实况图.jpg
```

也可以用 `--output` 自己指定输出文件名，扩展名建议写 `.jpg`，不要写成 `.png`。

## 指定输出封面尺寸

不指定 `--size` 时，输出封面尺寸就是封面图本身的尺寸。

如果你想生成手机竖图尺寸，例如 `3072x4096`：

```powershell
python "D:\Desktop\sk\create_live_photo.py" `
  --cover "D:\Desktop\1\1.jpg" `
  --video "D:\Desktop\1\1.mp4" `
  --output "D:\Desktop\1\1_created_live_photo_3072x4096.jpg" `
  --size 3072x4096
```

## 合成时的封面适配方式

只有指定 `--size` 后，`--fit` 才会明显影响结果。

可选值：

```text
crop     裁切填满，不留黑边，默认推荐
contain  完整显示新封面，可能出现黑边
stretch  强制拉伸到目标尺寸，可能变形
```

示例：

```powershell
python "D:\Desktop\sk\create_live_photo.py" `
  --cover "D:\Desktop\1\1.jpg" `
  --video "D:\Desktop\1\1.mp4" `
  --output "D:\Desktop\1\1_created_live_photo_contain.jpg" `
  --size 3072x4096 `
  --fit contain
```

## 调整合成 JPG 质量

默认质量是 95。

```powershell
python "D:\Desktop\sk\create_live_photo.py" `
  --cover "D:\Desktop\1\1.jpg" `
  --video "D:\Desktop\1\1.mp4" `
  --output "D:\Desktop\1\1_created_live_photo_q98.jpg" `
  --quality 98
```

## 关于动态效果识别

Windows 自带照片查看器通常只会把输出文件当成普通 JPG。

建议用下面这些方式测试：

- 手机图库 App
- Google Photos
- 支持 Live Photo / 实况照片的相册或图库软件

不同手机厂商对 Live Photo / 实况照片元数据的兼容程度不完全一样。如果某个相册只显示静态图，不一定是文件坏了，也可能是那个相册不识别这种单文件 Live Photo / 实况照片格式。
