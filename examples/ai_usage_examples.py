"""
AI Module Usage Examples

Demonstrates various ways to use the AI module in PRO-Ka-Po application.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.Modules.AI_module import (
    get_ai_manager, 
    AIProvider, 
    AIModel,
    PromptTemplates
)


def example_basic_usage():
    """Basic AI usage example"""
    print("=" * 60)
    print("EXAMPLE 1: Basic Usage")
    print("=" * 60)
    
    # Get AI manager
    ai = get_ai_manager()
    
    # Configure provider (using Gemini as example)
    api_key = os.getenv('GEMINI_API_KEY', 'demo-key')
    
    ai.set_provider(
        provider=AIProvider.GEMINI,
        api_key=api_key,
        model=AIModel.GEMINI_1_5_FLASH.value,
        temperature=0.7
    )
    
    # Generate response
    prompt = "In one sentence, explain what a Pomodoro timer is."
    print(f"\nPrompt: {prompt}")
    
    response = ai.generate(prompt)
    
    if response.error:
        print(f"❌ Error: {response.error}")
    else:
        print(f"✅ Response: {response.text}")
        print(f"📊 Model: {response.model}")
        print(f"⏱️  Timestamp: {response.timestamp}")
        if response.usage:
            print(f"🔢 Tokens: {response.usage}")


def example_alarm_suggestions():
    """Example: Get alarm suggestions for a task"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Alarm Suggestions")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    context = "User has an important presentation tomorrow at 10 AM and needs to prepare"
    
    prompt = PromptTemplates.alarm_suggestion(context)
    print(f"\nContext: {context}")
    
    response = ai.generate(prompt, use_cache=True)
    
    if not response.error:
        print(f"\n📅 Suggested Alarms:\n{response.text}")
    else:
        print(f"❌ Error: {response.error}")


def example_pomodoro_analysis():
    """Example: Analyze Pomodoro productivity"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Pomodoro Analysis")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    session_data = """
    - 8 sessions completed today
    - Average work duration: 23 minutes (target: 25)
    - 3 interruptions
    - Break duration: 5 minutes
    - Most productive time: 9 AM - 11 AM
    """
    
    prompt = PromptTemplates.pomodoro_analysis(session_data.strip())
    print(f"\nSession Data:\n{session_data}")
    
    response = ai.generate(prompt)
    
    if not response.error:
        print(f"\n🎯 Analysis:\n{response.text}")
    else:
        print(f"❌ Error: {response.error}")


def example_task_prioritization():
    """Example: Prioritize tasks with AI"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Task Prioritization")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    tasks = [
        "Fix critical bug in production",
        "Write documentation",
        "Review pull request",
        "Prepare for client meeting tomorrow",
        "Update project dependencies",
        "Team standup meeting"
    ]
    
    prompt = PromptTemplates.task_prioritization(tasks)
    print(f"\nTasks to prioritize:")
    for i, task in enumerate(tasks, 1):
        print(f"  {i}. {task}")
    
    response = ai.generate(prompt)
    
    if not response.error:
        print(f"\n📋 Prioritization:\n{response.text}")
    else:
        print(f"❌ Error: {response.error}")


def example_custom_prompt():
    """Example: Custom prompt for specific module"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Custom Prompt")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    prompt = PromptTemplates.custom(
        module="Alarms",
        context="User wants to build a healthy morning routine",
        instruction="Suggest 5 morning alarms with times and purposes to create a productive morning routine starting at 6 AM"
    )
    
    print(f"\nModule: Alarms")
    print(f"Context: Healthy morning routine")
    
    response = ai.generate(prompt)
    
    if not response.error:
        print(f"\n🌅 Morning Routine Suggestions:\n{response.text}")
    else:
        print(f"❌ Error: {response.error}")


def example_switching_providers():
    """Example: Switch between different AI providers"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Switching Providers")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    prompt = "Say 'Hello from [provider name]' in one sentence."
    
    providers_to_test = [
        (AIProvider.GEMINI, "GEMINI_API_KEY", AIModel.GEMINI_1_5_FLASH.value),
        (AIProvider.OPENAI, "OPENAI_API_KEY", AIModel.GPT_4O.value),
        (AIProvider.CLAUDE, "CLAUDE_API_KEY", AIModel.CLAUDE_3_5_SONNET.value),
    ]
    
    for provider, env_var, model in providers_to_test:
        api_key = os.getenv(env_var)
        
        if not api_key:
            print(f"\n⚠️  {provider.value.upper()}: No API key found (set {env_var})")
            continue
        
        try:
            ai.set_provider(
                provider=provider,
                api_key=api_key,
                model=model
            )
            
            response = ai.generate(prompt, use_cache=False)
            
            if not response.error:
                print(f"\n✅ {provider.value.upper()}: {response.text}")
            else:
                print(f"\n❌ {provider.value.upper()}: {response.error}")
                
        except Exception as e:
            print(f"\n❌ {provider.value.upper()}: {str(e)}")


def example_with_caching():
    """Example: Demonstrate response caching"""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Response Caching")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    prompt = "What are the benefits of the Pomodoro technique?"
    
    print(f"\nPrompt: {prompt}")
    print("\n1️⃣  First request (generates new response)...")
    response1 = ai.generate(prompt, use_cache=True)
    time1 = response1.timestamp
    
    if not response1.error:
        print(f"✅ Response received at {time1}")
        print(f"   {response1.text[:100]}...")
    
    print("\n2️⃣  Second request (uses cached response)...")
    response2 = ai.generate(prompt, use_cache=True)
    time2 = response2.timestamp
    
    if not response2.error:
        print(f"✅ Response received at {time2}")
        print(f"   Cached: {time1 == time2}")
    
    print("\n3️⃣  Third request with cache disabled...")
    response3 = ai.generate(prompt, use_cache=False)
    time3 = response3.timestamp
    
    if not response3.error:
        print(f"✅ New response at {time3}")
        print(f"   Different from cache: {time3 != time1}")


def example_available_models():
    """Example: Get available models for each provider"""
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Available Models")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    # Need to set a provider first (with dummy key for this example)
    providers = [
        AIProvider.GEMINI,
        AIProvider.OPENAI,
        AIProvider.GROK,
        AIProvider.CLAUDE,
        AIProvider.DEEPSEEK
    ]
    
    for provider in providers:
        try:
            ai.set_provider(provider=provider, api_key="demo-key")
            models = ai.get_available_models()
            
            print(f"\n📦 {provider.value.upper()} Models:")
            for model in models:
                print(f"   - {model}")
                
        except Exception as e:
            print(f"\n❌ {provider.value.upper()}: {str(e)}")


def example_error_handling():
    """Example: Proper error handling"""
    print("\n" + "=" * 60)
    print("EXAMPLE 9: Error Handling")
    print("=" * 60)
    
    ai = get_ai_manager()
    
    # Example 1: No provider configured
    print("\n1️⃣  Attempting to generate without provider...")
    try:
        # Create new instance to simulate no provider
        from src.Modules.AI_module.ai_logic import AIManager
        ai_new = AIManager()
        response = ai_new.generate("Test")
    except ValueError as e:
        print(f"✅ Caught expected error: {e}")
    
    # Example 2: Invalid API key
    print("\n2️⃣  Testing with invalid API key...")
    ai.set_provider(
        provider=AIProvider.GEMINI,
        api_key="invalid-key-12345"
    )
    
    response = ai.generate("Test prompt")
    if response.error:
        print(f"✅ Error handled gracefully: {response.error[:100]}...")
    
    # Example 3: Checking response before use
    print("\n3️⃣  Best practice: Always check for errors...")
    
    def safe_generate(prompt: str) -> str:
        """Safely generate AI response with error handling"""
        response = ai.generate(prompt)
        
        if response.error:
            return f"[AI Error: {response.error}]"
        else:
            return response.text
    
    result = safe_generate("What is Python?")
    print(f"✅ Safe result: {result[:100]}...")


def main():
    """Run all examples"""
    print("\n" + "🤖" * 30)
    print("AI MODULE USAGE EXAMPLES")
    print("🤖" * 30)
    
    # Check if API keys are set
    if not os.getenv('GEMINI_API_KEY') and not os.getenv('OPENAI_API_KEY'):
        print("\n⚠️  WARNING: No API keys found in environment variables")
        print("Set GEMINI_API_KEY or OPENAI_API_KEY to run full examples")
        print("\nExample:")
        print('  $env:GEMINI_API_KEY="your-key-here"  # PowerShell')
        print('  export GEMINI_API_KEY="your-key-here"  # Linux/Mac')
        print("\nProceeding with limited examples...\n")
    
    # Run examples
    try:
        # These work without API keys
        example_available_models()
        
        # These require API keys
        if os.getenv('GEMINI_API_KEY') or os.getenv('OPENAI_API_KEY'):
            example_basic_usage()
            example_alarm_suggestions()
            example_pomodoro_analysis()
            example_task_prioritization()
            example_custom_prompt()
            example_with_caching()
            example_switching_providers()
        
        example_error_handling()
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "✅" * 30)
    print("EXAMPLES COMPLETED")
    print("✅" * 30 + "\n")


if __name__ == "__main__":
    main()
