import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import aiohttp

async def main():
    image_path = r"F:\Antigravity\Cem_copok\.tmp\trader_dictionary.jpg"
    if not os.path.exists(image_path):
        print(f"❌ Image not found at {image_path}")
        return
        
    print(f"📡 Uploading {image_path} to Telegraph...")
    url = 'https://telegra.ph/upload'
    
    # Telegraph expects multipart upload with field name 'file' or 'file[]'
    data = aiohttp.FormData()
    with open(image_path, 'rb') as f:
        data.add_field('file', f.read(), filename='file.jpg', content_type='image/jpeg')
        
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as resp:
            if resp.status == 200:
                result = await resp.json()
                if isinstance(result, list) and len(result) > 0:
                    path = result[0].get('src')
                    full_url = f"https://telegra.ph{path}"
                    print(f"✅ Uploaded successfully! Public URL: {full_url}")
                else:
                    print(f"❌ Upload failed: {result}")
            else:
                text = await resp.text()
                print(f"❌ HTTP Error {resp.status}: {text}")

if __name__ == "__main__":
    asyncio.run(main())
