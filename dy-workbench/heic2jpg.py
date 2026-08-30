# HEIC/HEIF → JPEG 转换器（petdesk 换猫重绘用）
# 用法：stdin 传入 HEIC 原始字节，stdout 输出 JPEG 字节；退出码 0=成功
# 依赖：pillow-heif（psd_env）
import sys
import io


def main():
    data = sys.stdin.buffer.read()
    if not data:
        raise RuntimeError('stdin 为空')
    from pillow_heif import register_heif_opener
    from PIL import Image, ImageOps
    register_heif_opener()
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # 按 EXIF 方向转正
    if img.mode != 'RGB':
        img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=95)
    sys.stdout.buffer.write(buf.getvalue())


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        sys.stderr.write('HEIC 转换失败：%s\n' % e)
        sys.exit(1)
