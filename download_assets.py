import os
import urllib.request
from PIL import Image
import io

os.makedirs('assets/fonts', exist_ok=True)
os.makedirs('assets/img', exist_ok=True)
os.makedirs('assets/video', exist_ok=True)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def download_file(url, target_path):
    print(f"Downloading {url} -> {target_path}")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp, open(target_path, 'wb') as f:
        f.write(resp.read())
    print(f"Saved {target_path} ({os.path.getsize(target_path)} bytes)")

# Fonts
fonts = {
    'assets/fonts/chakra-s-700.woff2': 'https://fonts.gstatic.com/s/chakrapetch/v13/cIflMapbsEk7TDLdtEz1BwkeJI91R5_F.woff2',
    'assets/fonts/inter-s-400.woff2': 'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2',
    'assets/fonts/inter-s-700.woff2': 'https://fonts.gstatic.com/s/inter/v20/UcC73FwrK3iLTeHuS_nVMrMxCp50SjIa1ZL7.woff2',
}
for path, url in fonts.items():
    if not os.path.exists(path):
        download_file(url, path)

# Background image
img_png_url = 'https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/b5f79c5a-2ebd-41ef-865e-24c660ac98bd.png'
webp_target = 'assets/img/background.webp'
if not os.path.exists(webp_target):
    print("Downloading and converting background image...")
    req = urllib.request.Request(img_png_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    im = Image.open(io.BytesIO(data))
    im.save(webp_target, 'WEBP', quality=90)
    print(f"Saved {webp_target} ({os.path.getsize(webp_target)} bytes)")

# Videos
videos = {
    'assets/video/background.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_024808_abbfad57-4496-4906-9abc-49f0d153d287.mp4',
    'assets/video/expression.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_025948_2befd859-101e-49a4-8cb0-cdbb28cb11a7.mp4',
    'assets/video/craftsmanship.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_071544_17524fe8-2f07-4fbc-8a55-47518532df6f.mp4',
    'assets/video/refinement.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_025948_9fe460cc-21c2-476c-8e61-6bf57c2d6775.mp4',
    'assets/video/balance.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_072855_ba37e93c-1119-4b93-a3cd-6b29ced17dc2.mp4',
    'assets/video/origin.mp4': 'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260928_031433_64aea4c7-c53b-4e13-a1fc-bd73673b4fa5.mp4',
}

for path, url in videos.items():
    if not os.path.exists(path):
        try:
            download_file(url, path)
        except Exception as e:
            print(f"Failed to download {url}: {e}")

print("Assets setup completed successfully!")
