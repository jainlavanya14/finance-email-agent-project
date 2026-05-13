#!/usr/bin/env python3
"""Test if Gemini API key is valid and working."""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=" * 50)
print("🔍 GEMINI API TEST")
print("=" * 50)

if not api_key:
    print("❌ FAILED: No API key found in .env")
    sys.exit(1)

print(f"✅ API Key Found: {api_key[:20]}...")

try:
    print("🔄 Testing API connection...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-flash-latest")
    
    response = model.generate_content(
        contents="Say 'API is working' in one sentence.",
        generation_config={"temperature": 0.2, "max_output_tokens": 50}
    )
    
    print("✅ SUCCESS: API is working!")
    print(f"📝 Response: {response.text}")
    print("=" * 50)
    
except Exception as e:
    error_msg = str(e)[:300]
    print(f"❌ FAILED: {error_msg}")
    print("=" * 50)
    
    if "403" in error_msg:
        print("💡 Fix: Invalid API key. Get a new one from https://aistudio.google.com/app/apikey")
    elif "429" in error_msg:
        print("💡 Fix: Quota exceeded. Wait 24 hours for free tier reset.")
    elif "401" in error_msg:
        print("💡 Fix: Check your API key in .env file")
    
    sys.exit(1)
