"""
Test script to validate the MedCare AI CDSS project structure
Run this to ensure all imports and dependencies are working correctly
"""

import sys
import os
from pathlib import Path
import traceback

def test_imports():
    """Test all critical imports for the hackathon project"""
    print("🧪 Testing MedCare AI CDSS Project Structure")
    print("=" * 50)
    
    # Add project paths
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    src_dir = project_root / "src"
    
    sys.path.extend([str(src_dir), str(project_root)])
    
    results = {}
    
    # Test 1: Core dependencies
    print("\n📦 Testing Core Dependencies:")
    dependencies = [
        ('streamlit', 'streamlit'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('openai', 'openai'),
        ('sentence_transformers', 'sentence_transformers'),
        ('faiss', 'faiss'),
        ('reportlab', 'reportlab'),
        ('scikit-learn', 'sklearn'),
    ]
    
    for name, import_name in dependencies:
        try:
            __import__(import_name)
            print(f"  ✅ {name}")
            results[name] = True
        except ImportError as e:
            print(f"  ❌ {name}: {e}")
            results[name] = False
    
    # Test 2: Project structure
    print("\n📁 Testing Project Structure:")
    required_dirs = [
        "src",
        "src/core", 
        "src/ui",
        "src/utils",
        "data",
        "docs", 
        "tests",
        "scripts",
        "demo"
    ]
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  ✅ {dir_path}/")
            results[f"dir_{dir_path}"] = True
        else:
            print(f"  ❌ {dir_path}/ (missing)")
            results[f"dir_{dir_path}"] = False
    
    # Test 3: Key files
    print("\n📄 Testing Key Files:")
    required_files = [
        "README.md",
        "requirements.txt",
        "setup.py",
        "DEMO_SCRIPT.md",
        "src/core/clinical_engine.py",
        "src/ui/main_app.py",
        "src/utils/config.py",
        "data/drugbank_vectordb.pkl",
    ]
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
            results[f"file_{file_path}"] = True
        else:
            print(f"  ❌ {file_path} (missing)")
            results[f"file_{file_path}"] = False
    
    # Test 4: Module imports
    print("\n🔗 Testing Module Imports:")
    modules_to_test = [
        ('utils.config', 'config'),
        ('core.clinical_engine', 'MedicalKnowledgeBase'),
    ]
    
    for module_name, item_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
            print(f"  ✅ {module_name}.{item_name}")
            results[f"import_{module_name}"] = True
        except Exception as e:
            print(f"  ❌ {module_name}.{item_name}: {e}")
            results[f"import_{module_name}"] = False
    
    # Test 5: Environment configuration
    print("\n🔧 Testing Environment:")
    
    # Check OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print(f"  ✅ OPENAI_API_KEY configured")
        results['openai_key'] = True
    else:
        print(f"  ⚠️  OPENAI_API_KEY not set (required for AI features)")
        results['openai_key'] = False
    
    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 9):
        print(f"  ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        results['python_version'] = True
    else:
        print(f"  ❌ Python {python_version.major}.{python_version.minor} (requires 3.9+)")
        results['python_version'] = False
    
    # Summary
    print("\n📊 Test Summary:")
    print("=" * 20)
    total_tests = len(results)
    passed_tests = sum(results.values())
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 All tests passed! Project is ready for hackathon demo.")
        return True
    elif failed_tests <= 3:
        print("\n⚠️  Minor issues detected. Project should still work for demo.")
        return True
    else:
        print("\n❌ Major issues detected. Please resolve before demo.")
        return False

def main():
    """Main test function"""
    try:
        success = test_imports()
        if success:
            print("\n🚀 Ready to run: python -m streamlit run src/ui/main_app.py --server.port 8505")
        else:
            print("\n🔧 Please fix the issues above before running the demo.")
        
        return success
    except Exception as e:
        print(f"\n💥 Test script failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()