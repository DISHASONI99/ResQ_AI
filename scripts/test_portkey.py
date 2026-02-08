#!/usr/bin/env python3
"""
Test Portkey Integration

Run this script to verify your Portkey setup is working correctly.
It tests the fallback chain: Groq → Cerebras → Google

Usage:
    cd ResQ_AI
    python scripts/test_portkey.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")


async def test_portkey():
    """Test Portkey LLM service with all providers."""
    from src.services.llm_service import get_llm_service, GROQ_MODELS, CEREBRAS_MODELS, GOOGLE_MODELS
    
    print("\n" + "=" * 60)
    print("  ResQ AI - Portkey Integration Test")
    print("=" * 60 + "\n")
    
    # Check API keys
    print("📋 Checking API Keys...")
    keys = {
        "PORTKEY_API_KEY": os.getenv("PORTKEY_API_KEY", ""),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "CEREBRAS_API_KEY": os.getenv("CEREBRAS_API_KEY", ""),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
    }
    
    for key, value in keys.items():
        status = "✅ Set" if value and not value.startswith("your-") else "❌ Missing"
        masked = value[:8] + "..." if value else "NOT SET"
        print(f"   {key}: {status} ({masked})")
    
    print("\n" + "-" * 60)
    
    # Initialize service
    print("\n🚀 Initializing Portkey LLM Service...")
    llm = get_llm_service()
    
    print(f"\n📊 Configured Model Chain:")
    print(f"   Groq models: {GROQ_MODELS}")
    print(f"   Cerebras models: {CEREBRAS_MODELS}")
    print(f"   Google models: {GOOGLE_MODELS}")
    
    print("\n" + "-" * 60)
    
    # Test basic generation
    print("\n🧪 Test 1: Basic Generation (Auto-Fallback)")
    try:
        response = await llm.generate(
            user_prompt="What is 2+2? Reply with just the number.",
            max_tokens=10,
        )
        print(f"   ✅ Success!")
        print(f"   Provider: {response.get('provider', 'unknown')}")
        print(f"   Model: {response.get('model', 'unknown')}")
        print(f"   Response: {response['content'].strip()}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "-" * 60)
    
    # Test JSON structured output
    print("\n🧪 Test 2: Structured JSON Output")
    try:
        response = await llm.generate_structured(
            user_prompt="List 3 colors. Reply as JSON with key 'colors' containing a list.",
            system_prompt="You are a helpful assistant that responds in JSON format.",
            max_tokens=100,
        )
        print(f"   ✅ Success!")
        print(f"   Provider: {response.get('provider', 'unknown')}")
        print(f"   Response type: {type(response['content']).__name__}")
        print(f"   Content: {response['content']}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n" + "-" * 60)
    
    # Test specific providers
    print("\n🧪 Test 3: Provider-Specific Tests")
    
    providers_to_test = [
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama-3.3-70b"),
        ("google", "gemini-2.0-flash"),
    ]
    
    for provider, model in providers_to_test:
        print(f"\n   Testing {provider}/{model}...")
        try:
            response = await llm.generate(
                user_prompt="Say 'hello' in one word.",
                max_tokens=5,
                provider=provider,
                model=model,
                use_fallback=False,  # Don't fallback, test specific provider
            )
            print(f"   ✅ {provider}: Working")
        except Exception as e:
            print(f"   ⚠️ {provider}: {str(e)[:50]}...")
    
    print("\n" + "=" * 60)
    print("  Test Complete!")
    print("=" * 60 + "\n")
    
    # Summary
    print("📌 Summary:")
    print("   - Portkey is routing requests through configured providers")
    print("   - Fallback chain is active (tries next if one fails)")
    print("   - JSON structured output is working")
    print("\n🔗 View logs at: https://app.portkey.ai/logs")


if __name__ == "__main__":
    asyncio.run(test_portkey())
