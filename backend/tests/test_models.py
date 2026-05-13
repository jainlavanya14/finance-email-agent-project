#!/usr/bin/env python3
"""Test different Gemini models to find which one works."""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("🔍 GEMINI MODEL AVAILABILITY TEST")
print("=" * 60)

if not api_key:
    print("❌ FAILED: No API key found in .env")
    sys.exit(1)

print(f"✅ API Key: {api_key[:20]}...\n")

try:
    genai.configure(api_key=api_key)
    
    # List all available models
    print("📋 Checking available models...\n")
    models = genai.list_models()
    
    available_models = []
    for model in models:
        if "generateContent" in model.supported_generation_methods:
            available_models.append(model.name)
            print(f"✅ {model.name}")
    
    if not available_models:
        print("❌ No models available for generateContent")
        sys.exit(1)
    
    print(f"\n{'=' * 60}")
    print(f"Testing first available model: {available_models[0]}")
    print(f"{'=' * 60}\n")
    
    # Test the first available model
    model_name = available_models[0].split("/")[-1]  # Extract model name
    model = genai.GenerativeModel(model_name=model_name)
    
    print(f"🔄 Testing {model_name}...")
    response = model.generate_content(
        contents="Say 'API is working' in one sentence.",
        generation_config={"temperature": 0.2, "max_output_tokens": 50}
    )
    
    print(f"✅ SUCCESS: {model_name} is working!")
    print(f"📝 Response: {response.text}\n")
    print(f"{'=' * 60}")
    print(f"Use this in config: {model_name}")
    print(f"{'=' * 60}")
    
except Exception as e:
    error_msg = str(e)
    print(f"❌ FAILED: {error_msg[:300]}\n")
    
    if "403" in error_msg:
        print("⚠️  ISSUE: Access Denied (403)")
        print("   Possible causes:")
        print("   1. API key is invalid or revoked")
        print("   2. Project doesn't have billing enabled")
        print("   3. API is not enabled in project")
        print("\n   Solution:")
        print("   - Get NEW API key: https://aistudio.google.com/app/apikey")
        print("   - Or enable billing: https://console.cloud.google.com/billing")
    elif "429" in error_msg:
        print("⚠️  ISSUE: Quota Exceeded (429)")
        print("   Solution: Wait 24 hours for free tier reset")
    elif "401" in error_msg:
        print("⚠️  ISSUE: Unauthorized (401)")
        print("   Solution: Check your API key in .env")
    else:
        print("⚠️  ISSUE: Unknown error")
    
    sys.exit(1)
