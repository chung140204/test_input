"""test_api.py — Kiểm tra NVIDIA API key có hoạt động không"""
import requests

API_KEY = ''
MODEL   = 'meta/llama-3.2-90b-vision-instruct'
URL     = 'https://integrate.api.nvidia.com/v1/chat/completions'

print(f"\nĐang test với model {MODEL}...")
resp = requests.post(
    URL,
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json',
    },
    json={
        'model': MODEL,
        'messages': [{'role': 'user', 'content': 'Trả lời đúng 1 từ: 1+1=?'}],
        'max_tokens': 10,
    },
    timeout=30
)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    text = resp.json()['choices'][0]['message']['content']
    print(f"✅ API hoạt động! Response: {text.strip()}")
else:
    print(f"❌ Lỗi: {resp.text[:300]}")
