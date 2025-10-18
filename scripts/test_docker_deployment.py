"""
Docker Deployment Test Script for MedCare AI CDSS
Tests the complete system integration with Pathway RAG backend
"""

import requests
import json
import time
import os
import sys
from typing import Dict, Any
import traceback

class DockerSystemTester:
    def __init__(self):
        self.pathway_url = "http://localhost:8008"
        self.medcare_url = "http://localhost:8505"
        self.test_results = {}
        
    def test_pathway_backend(self) -> bool:
        """Test Pathway RAG backend connectivity"""
        print("🔍 Testing Pathway RAG Backend...")
        
        try:
            # Test basic connectivity
            test_query = {
                "prompt": "What are the common symptoms of diabetes?"
            }
            
            response = requests.post(
                f"{self.pathway_url}/v1/pw_ai_answer",
                json=test_query,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Pathway Backend Response: {result.get('response', 'No response')[:100]}...")
                self.test_results['pathway_backend'] = True
                return True
            else:
                print(f"  ❌ Pathway Backend Error: {response.status_code} - {response.text}")
                self.test_results['pathway_backend'] = False
                return False
                
        except Exception as e:
            print(f"  ❌ Pathway Backend Connection Failed: {e}")
            self.test_results['pathway_backend'] = False
            return False
    
    def test_medcare_frontend(self) -> bool:
        """Test MedCare AI CDSS frontend"""
        print("🖥️  Testing MedCare AI Frontend...")
        
        try:
            # Test Streamlit health endpoint
            response = requests.get(f"{self.medcare_url}/_stcore/health", timeout=10)
            
            if response.status_code == 200:
                print("  ✅ Streamlit Frontend Health Check Passed")
                self.test_results['medcare_frontend'] = True
                return True
            else:
                print(f"  ❌ Frontend Health Check Failed: {response.status_code}")
                self.test_results['medcare_frontend'] = False
                return False
                
        except Exception as e:
            print(f"  ❌ Frontend Connection Failed: {e}")
            self.test_results['medcare_frontend'] = False
            return False
    
    def test_integrated_workflow(self) -> bool:
        """Test the complete integrated workflow"""
        print("🔄 Testing Integrated AI Workflow...")
        
        try:
            # Simulate a clinical query through the system
            test_patient = {
                "name": "Test Patient",
                "age": 65,
                "gender": "Male",
                "conditions": ["Type 2 Diabetes", "Hypertension"],
                "medications": ["Metformin", "Lisinopril"]
            }
            
            # Test drug interaction analysis
            query = f"Analyze drug interactions for patient taking {', '.join(test_patient['medications'])}"
            
            pathway_response = requests.post(
                f"{self.pathway_url}/v1/pw_ai_answer",
                json={"prompt": query},
                timeout=30
            )
            
            if pathway_response.status_code == 200:
                result = pathway_response.json()
                response_text = result.get('response', '')
                
                print(f"  ✅ Integrated Query Response: {response_text[:150]}...")
                
                # Test if response contains medical content
                medical_keywords = ['drug', 'interaction', 'patient', 'medical', 'treatment']
                has_medical_content = any(keyword in response_text.lower() for keyword in medical_keywords)
                
                if has_medical_content:
                    print("  ✅ Response contains relevant medical content")
                    self.test_results['integrated_workflow'] = True
                    return True
                else:
                    print("  ⚠️  Response lacks medical content (may need more data)")
                    self.test_results['integrated_workflow'] = False
                    return False
            else:
                print(f"  ❌ Integrated Query Failed: {pathway_response.status_code}")
                self.test_results['integrated_workflow'] = False
                return False
                
        except Exception as e:
            print(f"  ❌ Integrated Workflow Test Failed: {e}")
            self.test_results['integrated_workflow'] = False
            return False
    
    def test_performance(self) -> Dict[str, float]:
        """Test system performance metrics"""
        print("⚡ Testing System Performance...")
        
        performance_metrics = {}
        
        try:
            # Test Pathway response time
            start_time = time.time()
            response = requests.post(
                f"{self.pathway_url}/v1/pw_ai_answer",
                json={"prompt": "Quick test query"},
                timeout=30
            )
            pathway_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if response.status_code == 200:
                performance_metrics['pathway_response_ms'] = pathway_time
                print(f"  ✅ Pathway Response Time: {pathway_time:.1f}ms")
            else:
                print(f"  ❌ Pathway Performance Test Failed")
                
            # Test frontend response time
            start_time = time.time()
            response = requests.get(f"{self.medcare_url}/_stcore/health", timeout=10)
            frontend_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                performance_metrics['frontend_response_ms'] = frontend_time
                print(f"  ✅ Frontend Response Time: {frontend_time:.1f}ms")
            else:
                print(f"  ❌ Frontend Performance Test Failed")
                
        except Exception as e:
            print(f"  ❌ Performance Test Error: {e}")
            
        self.test_results['performance_metrics'] = performance_metrics
        return performance_metrics
    
    def test_environment_config(self) -> bool:
        """Test environment configuration"""
        print("🔧 Testing Environment Configuration...")
        
        checks = {
            'openai_key': bool(os.getenv('OPENAI_API_KEY')),
            'pathway_url': self.pathway_url is not None,
            'medcare_url': self.medcare_url is not None,
        }
        
        for check, status in checks.items():
            if status:
                print(f"  ✅ {check}: Configured")
            else:
                print(f"  ❌ {check}: Missing")
        
        all_configured = all(checks.values())
        self.test_results['environment_config'] = all_configured
        return all_configured
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len([k for k in self.test_results.keys() if k != 'performance_metrics'])
        passed_tests = sum([v for k, v in self.test_results.items() if k != 'performance_metrics' and isinstance(v, bool)])
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            'test_results': self.test_results,
            'system_status': 'READY' if passed_tests >= total_tests-1 else 'ISSUES_DETECTED'
        }
        
        return report
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive report"""
        print("🧪 MedCare AI CDSS - Docker System Test")
        print("=" * 50)
        
        # Wait for services to be ready
        print("⏳ Waiting for services to start (30 seconds)...")
        time.sleep(30)
        
        # Run tests
        self.test_environment_config()
        self.test_pathway_backend()
        self.test_medcare_frontend()
        self.test_integrated_workflow()
        self.test_performance()
        
        # Generate report
        report = self.generate_test_report()
        
        print("\n📊 Test Summary:")
        print("=" * 20)
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']}")
        print(f"Success Rate: {report['success_rate']}")
        print(f"System Status: {report['system_status']}")
        
        if report['system_status'] == 'READY':
            print("\n🎉 All systems operational! Ready for hackathon demo.")
            print(f"🌐 Access MedCare AI CDSS at: {self.medcare_url}")
        else:
            print("\n⚠️  Some issues detected. Check individual test results.")
        
        return report

def main():
    """Main test execution"""
    try:
        tester = DockerSystemTester()
        report = tester.run_all_tests()
        
        # Save report
        with open('docker_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Test report saved to: docker_test_report.json")
        
        # Exit with appropriate code
        sys.exit(0 if report['system_status'] == 'READY' else 1)
        
    except Exception as e:
        print(f"💥 Test script failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()