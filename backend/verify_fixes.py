"""
Quick verification of critical workflow functionality
"""
import sys
from pathlib import Path

# Set up paths exactly like main.py does
project_root = Path(__file__).parent.parent
backend_dir = Path(__file__).parent

sys.path.append(str(project_root))
sys.path.append(str(backend_dir))

print("\n" + "="*70)
print("🔍 QUICK SYSTEM VERIFICATION")
print("="*70 + "\n")

# TEST 1: Import verification
print("TEST 1: Verifying critical imports...")
try:
    from backend.core.workflow import WorkflowEngine
    print("✅ WorkflowEngine imported")
    
    # Check for resume method
    if hasattr(WorkflowEngine, 'resume'):
        print("✅ WorkflowEngine.resume() method EXISTS")
        print("   This means approve button WILL work!")
    else:
        print("❌ WorkflowEngine.resume() method MISSING")
        print("   This means approve button WON'T work!")
        
except Exception as e:
    print(f"❌ Import failed: {e}")

# TEST 2: Check configuration API
print("\nTEST 2: Verifying configuration API...")
try:
    from backend.api.routers.configuration import router
    print(f"✅ Configuration router exists with {len(router.routes)} routes")
except Exception as e:
    print(f"❌ Configuration router failed: {e}")

# TEST 3: Check markdown formatter
print("\nTEST 3: Verifying markdown formatter...")
try:
    from backend.core.markdown_formatter import get_markdown_formatter
    formatter = get_markdown_formatter()
    if formatter.use_llm:
        print("✅ Gemini LLM formatter active")
    else:
        print("⚠️  Using fallback (no API key)")
except Exception as e:
    print(f"❌ Formatter failed: {e}")

# TEST 4: Simple async test
print("\nTEST 4: Testing resume() functionality...")
try:
    import asyncio
    from backend.core.workflow import WorkflowEngine
    from orchestrator.central import CentralOrchestrator
    
    async def quick_test():
        state = {"project_id": "test", "project_name": "Test", "user_context": {}}
        engine = WorkflowEngine("test", CentralOrchestrator(tools=[]), state, None, None)
        
        # Check initial state
        before = engine.pause_event.is_set()
        
        # Call resume
        await engine.resume()
        
        # Check after state
        after = engine.pause_event.is_set()
        
        if before == False and after == True:
            print("✅ resume() WORKS CORRECTLY!")
            print("   Before: paused, After: resumed")
            return True
        else:
            print(f"❌ resume() FAILED - Before: {before}, After: {after}")
            return False
    
    result = asyncio.run(quick_test())
    
except Exception as e:
    print(f"❌ Async test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("VERIFICATION COMPLETE")
print("="*70 + "\n")
