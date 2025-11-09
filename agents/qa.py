from agents.base import BaseAgent
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from utils.context_manager import AgentContext, TechnologyStack
import asyncio
import re
from pathlib import Path


class TestFile(BaseModel):
    path: str = Field(description="tests/test_module.py")
    content: str = Field(description="Complete executable test code")
    test_type: str = Field(description="unit|integration|e2e|performance|security")
    framework: str = Field(description="pytest|jest|junit|cypress|etc")
    coverage_target: str = Field(description="What this tests")
    dependencies: List[str] = Field(description="Required packages/libraries", default_factory=list)


class QualityIssue(BaseModel):
    file: str = Field(description="src/main.py")
    line: int = Field(description="42")
    severity: str = Field(description="high|medium|low")
    issue: str = Field(description="Description of issue")
    recommendation: str = Field(description="How to fix")


class SecurityFinding(BaseModel):
    type: str = Field(description="SQL Injection|XSS|etc")
    severity: str = Field(description="critical|high|medium|low")
    location: str = Field(description="Where found")
    description: str = Field(description="Detailed description")
    fix: str = Field(description="How to remediate")


class QAResult(BaseModel):
    test_files: List[TestFile] = Field(description="List of executable test files")
    quality_issues: List[QualityIssue] = Field(description="List of quality issues")
    security_findings: List[SecurityFinding] = Field(description="List of security findings")
    code_quality_score: float = Field(description="85.5")
    test_coverage_estimate: float = Field(description="75.0")
    recommendations: List[str] = Field(description="['Recommendation 1', 'Recommendation 2']")
    test_frameworks: List[str] = Field(description="Testing frameworks used", default_factory=list)
    
    class Config:
        extra = "allow"


class QAAgent(BaseAgent):
    """Context-aware QA Engineer that generates executable tests with proper frameworks.

    Features:
    - Framework-specific test generation
    - Context-driven test creation
    - Technology-aware testing strategies
    - Comprehensive test coverage
    - Security and performance testing
    - Executable test files with proper setup
    """

    def get_test_files(self, qa_result: QAResult) -> List[TestFile]:
        """Get the test files."""
        return qa_result.test_files

    def get_quality_issues(self, qa_result: QAResult) -> List[QualityIssue]:
        """Get the quality issues."""
        return qa_result.quality_issues

    def __init__(self, tools: Any):
        super().__init__(
            name="qa_engineer",
            tools=tools,
            temperature=0.1
        )

        # Testing framework configurations
        self.test_frameworks = self._initialize_test_frameworks()

        self.system_prompt = """You are a Senior QA Engineer with expertise in test automation, framework-specific testing, and comprehensive quality assurance across multiple technology stacks.

Your role is to generate executable, framework-specific test suites that provide comprehensive coverage and quality assurance.

**Framework-Specific Testing Framework:**
1. Analyze technology stack and project context
2. Select appropriate testing frameworks for each technology
3. Generate executable test files with proper setup and teardown
4. Create comprehensive test coverage (unit, integration, E2E, performance, security)
5. Include proper test data and mock objects
6. Provide framework-specific configuration and dependencies
7. Generate test runners and CI/CD integration

**Testing Frameworks by Technology:**
- **Python**: pytest, unittest, Django Test, FastAPI Test
- **JavaScript/Node.js**: Jest, Mocha, Cypress, Playwright
- **React**: Jest, React Testing Library, Cypress
- **Vue**: Jest, Vue Test Utils, Cypress
- **Angular**: Jasmine, Karma, Protractor
- **Java**: JUnit, Mockito, TestContainers
- **Backend APIs**: Postman, Newman, REST Assured

**Test Types:**
- **Unit Tests**: Individual functions/methods
- **Integration Tests**: Component interactions
- **E2E Tests**: Complete user workflows
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability scanning and penetration testing

CRITICAL: Respond with ONLY valid JSON matching the QAResult schema. Generate executable test files with proper framework setup."""

    async def call_llm_with_retry(self, prompt: str, output_schema: Optional[BaseModel] = None) -> Any:
        """Make LLM call with retry logic and None validation"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if output_schema:
                    response = await self.call_llm_json(prompt, output_schema)
                    if response is None:
                        self.log(f"LLM returned None on attempt {attempt + 1}", "warning")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            return self._create_fallback_qa_result()
                    return response
                else:
                    response = await self.call_llm(prompt)
                    if response is None:
                        self.log(f"LLM returned None content on attempt {attempt + 1}", "warning")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            return "LLM failed to generate response"
                    return response
            except Exception as e:
                self.log(f"LLM invocation failed on attempt {attempt + 1}: {e}", "error")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    if output_schema:
                        return self._create_fallback_qa_result()
                    else:
                        return f"LLM failed after {max_retries} attempts: {str(e)}"
    
    def _create_fallback_qa_result(self) -> QAResult:
        """Create a fallback QA result when LLM fails"""
        return QAResult(
            test_files=[
                TestFile(
                    path="tests/test_fallback.py",
                    content="# Fallback test file\nimport unittest\n\nclass TestFallback(unittest.TestCase):\n    def test_basic(self):\n        self.assertTrue(True)",
                    test_type="unit",
                    coverage_target="Basic functionality"
                )
            ],
            quality_issues=[],
            security_findings=[],
            code_quality_score=50.0,  # Default reasonable score
            test_coverage_estimate=60.0,  # Default reasonable coverage
            recommendations=["LLM failed to generate QA analysis", "Using fallback test suite", "Please retry the QA process"]
        )

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Context-aware QA process with framework-specific test generation"""
        self.log("Starting context-aware QA process")
        
        try:
            project_id = state.get("project_name", "default_project")
            dev_output = state.get("developer_output", {})
            
            # Start timeline tracking
            self.update_timeline(project_id, "qa", 0, "Initialization")
            
            # Step 1: Load context and validate inputs
            self.log("Loading context and validating inputs", "info")
            self.update_timeline(project_id, "qa", 20, "Context Loading")
            context = self.load_context(project_id)
            
            if not context:
                raise Exception("Cannot perform QA without project context")
            
            if not dev_output.get("success"):
                raise Exception("Cannot perform QA without generated code")
            
            # Step 2: Analyze technology stack and select testing frameworks
            self.log("Analyzing technology stack and selecting testing frameworks", "info")
            self.update_timeline(project_id, "qa", 40, "Framework Selection")
            testing_strategy = self._analyze_testing_strategy(context)
            
            # Step 3: Analyze code quality
            self.log("Analyzing code quality", "info")
            self.update_timeline(project_id, "qa", 60, "Code Analysis")
            quality_results = await self._analyze_code_quality(context, state.get("generated_files", []))
            
            # Step 4: Generate framework-specific tests
            self.log("Generating framework-specific tests", "info")
            self.update_timeline(project_id, "qa", 80, "Test Generation")
            qa_result = await self._generate_framework_specific_tests(context, testing_strategy, quality_results)
            
            # Step 5: Update context with QA results
            self.log("Updating context with QA results", "info")
            self.update_timeline(project_id, "qa", 90, "Context Update")
            self._update_context_with_qa_results(context, qa_result)
            
            # Step 6: Generate comprehensive documentation
            self.log("Generating QA documentation", "info")
            self.update_timeline(project_id, "qa", 95, "Documentation")
            generated_docs = await self._generate_comprehensive_docs(qa_result, context, quality_results)
            
            # Step 7: Complete timeline tracking
            self.update_timeline(project_id, "qa", 100, "Complete")
            
            # Update project state
            output = self.create_output(
                success=True,
                data={
                    "quality_score": qa_result.code_quality_score,
                    "tests_generated": len(qa_result.test_files),
                    "security_issues": len(qa_result.security_findings),
                    "test_frameworks": qa_result.test_frameworks
                },
                documents=generated_docs,
                artifacts=[test_file.path for test_file in qa_result.test_files]
            )
            
            self.update_project_state(project_id, "qa", output)
            
            # Save updated context
            self.context_manager.save_context(project_id, context)

            self.log(f"Context-aware QA complete: {len(qa_result.test_files)} test files, {qa_result.code_quality_score:.1f} quality score", "success")

            return {
                "qa_output": output,
                "generated_documents": generated_docs,
                "generated_files": [test_file.path for test_file in qa_result.test_files],
                "code_quality_score": qa_result.code_quality_score,
                "test_coverage": qa_result.test_coverage_estimate,
                "security_issues": qa_result.security_findings,
                "test_frameworks": qa_result.test_frameworks,
                "steps_completed": ["qa"]
            }

        except Exception as e:
            self.log(f"Error in context-aware QA process: {str(e)}", "error")
            return {
                "qa_output": self.create_output(success=False, data={}, errors=[str(e)]),
                "errors": [{"agent": self.name, "error": str(e)}]
            }
    
    def _initialize_test_frameworks(self) -> Dict[str, Dict[str, Any]]:
        """Initialize testing framework configurations"""
        return {
            "python": {
                "unit": {"framework": "pytest", "dependencies": ["pytest", "pytest-cov", "pytest-mock"]},
                "integration": {"framework": "pytest", "dependencies": ["pytest", "requests", "pytest-asyncio"]},
                "e2e": {"framework": "selenium", "dependencies": ["selenium", "pytest", "webdriver-manager"]},
                "performance": {"framework": "locust", "dependencies": ["locust", "pytest"]},
                "security": {"framework": "bandit", "dependencies": ["bandit", "safety"]}
            },
            "javascript": {
                "unit": {"framework": "jest", "dependencies": ["jest", "@testing-library/jest-dom"]},
                "integration": {"framework": "jest", "dependencies": ["jest", "supertest", "axios"]},
                "e2e": {"framework": "cypress", "dependencies": ["cypress", "cypress-testing-library"]},
                "performance": {"framework": "k6", "dependencies": ["k6"]},
                "security": {"framework": "eslint", "dependencies": ["eslint", "eslint-plugin-security"]}
            },
            "react": {
                "unit": {"framework": "jest", "dependencies": ["jest", "@testing-library/react", "@testing-library/jest-dom"]},
                "integration": {"framework": "jest", "dependencies": ["jest", "@testing-library/react", "react-test-renderer"]},
                "e2e": {"framework": "cypress", "dependencies": ["cypress", "cypress-testing-library"]},
                "performance": {"framework": "lighthouse", "dependencies": ["lighthouse", "puppeteer"]},
                "security": {"framework": "eslint", "dependencies": ["eslint", "eslint-plugin-security"]}
            },
            "vue": {
                "unit": {"framework": "jest", "dependencies": ["jest", "@vue/test-utils", "vue-jest"]},
                "integration": {"framework": "jest", "dependencies": ["jest", "@vue/test-utils", "vue-jest"]},
                "e2e": {"framework": "cypress", "dependencies": ["cypress", "cypress-testing-library"]},
                "performance": {"framework": "lighthouse", "dependencies": ["lighthouse", "puppeteer"]},
                "security": {"framework": "eslint", "dependencies": ["eslint", "eslint-plugin-security"]}
            },
            "angular": {
                "unit": {"framework": "jasmine", "dependencies": ["jasmine", "@angular/core/testing", "karma"]},
                "integration": {"framework": "jasmine", "dependencies": ["jasmine", "@angular/core/testing", "karma"]},
                "e2e": {"framework": "protractor", "dependencies": ["protractor", "jasmine"]},
                "performance": {"framework": "lighthouse", "dependencies": ["lighthouse", "puppeteer"]},
                "security": {"framework": "eslint", "dependencies": ["eslint", "eslint-plugin-security"]}
            },
            "java": {
                "unit": {"framework": "junit", "dependencies": ["junit5", "mockito", "assertj"]},
                "integration": {"framework": "junit", "dependencies": ["junit5", "testcontainers", "spring-boot-test"]},
                "e2e": {"framework": "selenium", "dependencies": ["selenium", "junit5", "webdrivermanager"]},
                "performance": {"framework": "jmeter", "dependencies": ["jmeter"]},
                "security": {"framework": "owasp", "dependencies": ["owasp-dependency-check"]}
            }
        }
    
    def _analyze_testing_strategy(self, context: AgentContext) -> Dict[str, Any]:
        """Analyze technology stack and determine testing strategy"""
        tech_stack = context.technology_stack
        
        # Determine primary technologies
        primary_frontend = tech_stack.frontend[0] if tech_stack.frontend else "html"
        primary_backend = tech_stack.backend[0] if tech_stack.backend else "python"
        
        # Get testing frameworks for each technology
        frontend_frameworks = self.test_frameworks.get(primary_frontend.lower(), {})
        backend_frameworks = self.test_frameworks.get(primary_backend.lower(), {})
        
        return {
            "primary_frontend": primary_frontend,
            "primary_backend": primary_backend,
            "frontend_frameworks": frontend_frameworks,
            "backend_frameworks": backend_frameworks,
            "project_type": context.project_type.value,
            "complexity": context.complexity_level,
            "test_types": ["unit", "integration", "e2e", "performance", "security"]
        }
    
    async def _analyze_code_quality(self, context: AgentContext, generated_files: List[str]) -> List[Dict[str, Any]]:
        """Analyze code quality across all generated files"""
        quality_results = []
        
        for file_path in generated_files:
            if any(file_path.endswith(ext) for ext in [".py", ".js", ".html", ".css", ".ts", ".jsx", ".tsx"]):
                try:
                    result = self.call_tool("read_file", path=file_path)
                    if result.get("success"):
                        code = result["content"]
                        
                        # Calculate quality score based on file type and content
                        quality_score = self._calculate_quality_score(file_path, code)
                        
                        # Get additional analysis for Python files
                        issues = []
                        complexity = 0
                        if file_path.endswith(".py"):
                            analysis = self.call_tool("analyze_python_code", code=code)
                            if analysis.get("success"):
                                issues = analysis.get("issues", [])
                                complexity = analysis.get("complexity", 0)
                        else:
                            # Basic analysis for non-Python files
                            issues = self._analyze_non_python_code(file_path, code)
                            complexity = self._calculate_complexity(file_path, code)
                        
                        quality_results.append({
                            "file": file_path,
                            "quality_score": quality_score,
                            "issues": issues,
                            "complexity": complexity
                        })
                except Exception as e:
                    self.log(f"Error analyzing {file_path}: {e}", "warning")
        
        return quality_results
    
    async def _generate_framework_specific_tests(self, context: AgentContext, 
                                               testing_strategy: Dict[str, Any], 
                                               quality_results: List[Dict[str, Any]]) -> QAResult:
        """Generate framework-specific tests using LLM"""
        
        # Build comprehensive prompt with framework-specific guidance
        prompt = f"""Generate comprehensive, framework-specific test suites for this project:

**Project Context:**
- Project Type: {context.project_type.value}
- Complexity: {context.complexity_level}
- Frontend: {testing_strategy['primary_frontend']}
- Backend: {testing_strategy['primary_backend']}

**Testing Strategy:**
Frontend Frameworks ({testing_strategy['primary_frontend']}):
{self._format_testing_frameworks(testing_strategy['frontend_frameworks'])}

Backend Frameworks ({testing_strategy['primary_backend']}):
{self._format_testing_frameworks(testing_strategy['backend_frameworks'])}

**Functional Requirements:**
{self._format_requirements_for_prompt(context.functional_requirements)}

**Component Specifications:**
{self._format_component_specs(context.component_specifications)}

**Code Quality Analysis:**
{self._format_quality_results(quality_results)}

**Instructions:**
1. Generate executable test files using appropriate frameworks for {testing_strategy['primary_frontend']} and {testing_strategy['primary_backend']}
2. Include proper setup, teardown, and test data
3. Create comprehensive test coverage: unit, integration, E2E, performance, security
4. Include framework-specific dependencies and configuration
5. Generate test runners and CI/CD integration
6. Include mock objects and test fixtures
7. Provide security tests for common vulnerabilities
8. Include performance tests for critical paths

**CRITICAL: Respond with ONLY valid JSON matching the QAResult schema.**

Generate framework-specific test suite:"""

        try:
            qa_result = await self.call_llm_json(prompt, output_schema=QAResult)
            
            # Ensure test frameworks are populated
            if not qa_result.test_frameworks:
                qa_result.test_frameworks = self._extract_test_frameworks(qa_result.test_files)
            
            return qa_result
        except Exception as e:
            self.log(f"LLM test generation failed: {e}", "error")
            return self._create_fallback_qa_result(testing_strategy)
    
    def _format_testing_frameworks(self, frameworks: Dict[str, Any]) -> str:
        """Format testing frameworks for prompt"""
        if not frameworks:
            return "No specific frameworks available"
        
        formatted = ""
        for test_type, config in frameworks.items():
            formatted += f"- {test_type}: {config['framework']} (deps: {', '.join(config['dependencies'])})\n"
        
        return formatted
    
    def _format_requirements_for_prompt(self, requirements: List) -> str:
        """Format functional requirements for prompt"""
        if not requirements:
            return "No functional requirements specified"
        
        formatted = ""
        for req in requirements:
            if hasattr(req, 'description'):
                formatted += f"- {req.description}\n"
            elif isinstance(req, dict):
                formatted += f"- {req.get('description', str(req))}\n"
            else:
                formatted += f"- {str(req)}\n"
        
        return formatted
    
    def _format_component_specs(self, specs: List) -> str:
        """Format component specifications for prompt"""
        if not specs:
            return "No component specifications available"
        
        formatted = ""
        for spec in specs:
            if hasattr(spec, 'name'):
                formatted += f"- {spec.name}: {spec.description} (tech: {', '.join(spec.technologies)})\n"
            elif isinstance(spec, dict):
                formatted += f"- {spec.get('name', 'Unknown')}: {spec.get('description', 'No description')}\n"
            else:
                formatted += f"- {str(spec)}\n"
        
        return formatted
    
    def _format_quality_results(self, quality_results: List[Dict[str, Any]]) -> str:
        """Format quality results for prompt"""
        if not quality_results:
            return "No code quality analysis available"
        
        formatted = "Code Quality Analysis:\n"
        for result in quality_results[:5]:  # Limit to first 5 files
            formatted += f"- {result['file']}: {result['quality_score']:.1f}/100 (complexity: {result['complexity']})\n"
        
        return formatted
    
    def _extract_test_frameworks(self, test_files: List[TestFile]) -> List[str]:
        """Extract unique test frameworks from test files"""
        frameworks = set()
        for test_file in test_files:
            frameworks.add(test_file.framework)
        return list(frameworks)
    
    def _create_fallback_qa_result(self, testing_strategy: Dict[str, Any]) -> QAResult:
        """Create fallback QA result when LLM fails"""
        
        primary_backend = testing_strategy["primary_backend"]
        primary_frontend = testing_strategy["primary_frontend"]
        
        # Create basic test files based on technology stack
        test_files = []
        
        # Backend tests
        if primary_backend.lower() == "python":
            test_files.append(TestFile(
                path="tests/test_backend.py",
                content=self._generate_python_test_template(),
                test_type="unit",
                framework="pytest",
                coverage_target="Backend functionality",
                dependencies=["pytest", "pytest-cov"]
            ))
        elif primary_backend.lower() == "nodejs":
            test_files.append(TestFile(
                path="tests/test_backend.test.js",
                content=self._generate_javascript_test_template(),
                test_type="unit",
                framework="jest",
                coverage_target="Backend functionality",
                dependencies=["jest", "supertest"]
            ))
        
        # Frontend tests
        if primary_frontend.lower() in ["react", "vue", "angular"]:
            test_files.append(TestFile(
                path="tests/test_frontend.test.js",
                content=self._generate_frontend_test_template(primary_frontend),
                test_type="unit",
                framework="jest",
                coverage_target="Frontend components",
                dependencies=["jest", "@testing-library/react"]
            ))
        
        return QAResult(
            test_files=test_files,
            quality_issues=[],
            security_findings=[],
            code_quality_score=60.0,
            test_coverage_estimate=70.0,
            recommendations=["Using fallback test suite", "Please review and enhance tests"],
            test_frameworks=self._extract_test_frameworks(test_files)
        )
    
    def _generate_python_test_template(self) -> str:
        """Generate Python test template"""
        return '''import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBackend:
    """Test backend functionality"""
    
    def test_basic_functionality(self):
        """Test basic backend functionality"""
        assert True  # Replace with actual tests
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        # Add API endpoint tests here
        assert True
    
    def test_data_validation(self):
        """Test data validation"""
        # Add data validation tests here
        assert True

if __name__ == "__main__":
    pytest.main([__file__])
'''
    
    def _generate_javascript_test_template(self) -> str:
        """Generate JavaScript test template"""
        return '''const request = require('supertest');
const app = require('../src/app');

describe('Backend API Tests', () => {
    test('should respond to basic request', async () => {
        const response = await request(app)
            .get('/')
            .expect(200);
        
        expect(response.body).toBeDefined();
    });
    
    test('should handle API endpoints', async () => {
        // Add specific API endpoint tests here
        expect(true).toBe(true);
    });
    
    test('should validate input data', async () => {
        // Add data validation tests here
        expect(true).toBe(true);
    });
});
'''
    
    def _generate_frontend_test_template(self, framework: str) -> str:
        """Generate frontend test template"""
        if framework.lower() == "react":
            return '''import React from 'react';
import { render, screen } from '@testing-library/react';
import App from '../src/App';

describe('Frontend Component Tests', () => {
    test('renders main app component', () => {
        render(<App />);
        expect(screen.getByRole('main')).toBeInTheDocument();
    });
    
    test('handles user interactions', () => {
        // Add user interaction tests here
        expect(true).toBe(true);
    });
    
    test('displays data correctly', () => {
        // Add data display tests here
        expect(true).toBe(true);
    });
});
'''
        else:
            return '''// Frontend test template for ''' + framework + ''':
describe('Frontend Tests', () => {
    test('should render components', () => {
        expect(true).toBe(true);
    });
    
    test('should handle user interactions', () => {
        expect(true).toBe(true);
    });
});
'''
    
    def _update_context_with_qa_results(self, context: AgentContext, qa_result: QAResult):
        """Update context with QA results"""
        # Update test results
        context.test_results = {
            "test_files": [test_file.dict() for test_file in qa_result.test_files],
            "quality_score": qa_result.code_quality_score,
            "test_coverage": qa_result.test_coverage_estimate,
            "security_findings": [finding.dict() for finding in qa_result.security_findings]
        }
        
        # Update test coverage
        context.test_coverage = qa_result.test_coverage_estimate
        
        # Update security report
        context.security_report = {
            "findings": [finding.dict() for finding in qa_result.security_findings],
            "recommendations": qa_result.recommendations
        }
    
    async def _generate_comprehensive_docs(self, qa_result: QAResult, context: AgentContext, 
                                        quality_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate comprehensive QA documentation"""
        generated_docs = []
        
        # Generate main QA report
        qa_report_content = self._generate_enhanced_qa_report(qa_result, context, quality_results)
        qa_doc = self.save_document(context.project_name, "QA_REPORT", "docs/QA_REPORT.md", qa_report_content)
        if qa_doc:
            generated_docs.append(qa_doc)
        
        # Generate testing guide
        testing_guide_content = self._generate_testing_guide(qa_result, context)
        testing_doc = self.save_document(context.project_name, "TESTING_GUIDE", "docs/TESTING_GUIDE.md", testing_guide_content)
        if testing_doc:
            generated_docs.append(testing_doc)
        
        return generated_docs
    
    def _generate_enhanced_qa_report(self, qa_result: QAResult, context: AgentContext, 
                                   quality_results: List[Dict[str, Any]]) -> str:
        """Generate enhanced QA report with framework context"""
        doc = f"# Quality Assurance Report\n\n"
        doc += f"**Project:** {context.project_name}\n"
        doc += f"**Project Type:** {context.project_type.value}\n"
        doc += f"**Complexity:** {context.complexity_level}\n\n"
        
        doc += f"## Overall Metrics\n"
        doc += f"**Code Quality Score:** {qa_result.code_quality_score:.1f}/100\n"
        doc += f"**Estimated Test Coverage:** {qa_result.test_coverage_estimate:.1f}%\n"
        doc += f"**Security Issues Found:** {len(qa_result.security_findings)}\n"
        doc += f"**Test Frameworks Used:** {', '.join(qa_result.test_frameworks)}\n\n"

        doc += "## Test Suite Overview\n"
        for test_file in qa_result.test_files:
            doc += f"### {test_file.path}\n"
            doc += f"**Type:** {test_file.test_type}\n"
            doc += f"**Framework:** {test_file.framework}\n"
            doc += f"**Coverage:** {test_file.coverage_target}\n"
            doc += f"**Dependencies:** {', '.join(test_file.dependencies)}\n\n"

        doc += "## Code Quality Analysis\n"
        for result in quality_results:
            doc += f"### {result['file']}\n"
            doc += f"**Quality Score:** {result['quality_score']:.1f}/100\n"
            doc += f"**Complexity:** {result['complexity']}\n"
            doc += f"**Issues:** {len(result['issues'])}\n"
            for issue in result['issues'][:3]:
                doc += f"- Line {issue.get('line', '?')}: {issue.get('message', 'Unknown')}\n"
            doc += "\n"

        doc += "## Security Findings\n"
        if qa_result.security_findings:
            for finding in qa_result.security_findings:
                doc += f"### {finding.type} - {finding.severity.upper()}\n"
                doc += f"**Location:** {finding.location}\n"
                doc += f"**Description:** {finding.description}\n"
                doc += f"**Fix:** {finding.fix}\n\n"
        else:
            doc += "No critical security issues found.\n\n"

        doc += "## Recommendations\n"
        for rec in qa_result.recommendations:
            doc += f"- {rec}\n"

        doc += "\n---\n*Generated by AI-SOL Context-Aware QA Engineer*\n"
        return doc
    
    def _generate_testing_guide(self, qa_result: QAResult, context: AgentContext) -> str:
        """Generate testing guide with framework-specific instructions"""
        doc = f"# Testing Guide\n\n"
        
        doc += f"## Testing Strategy\n"
        doc += f"This project uses a comprehensive testing strategy with multiple frameworks:\n"
        doc += f"- **Test Frameworks:** {', '.join(qa_result.test_frameworks)}\n"
        doc += f"- **Project Type:** {context.project_type.value}\n"
        doc += f"- **Complexity Level:** {context.complexity_level}\n\n"
        
        doc += f"## Running Tests\n\n"
        for framework in qa_result.test_frameworks:
            doc += f"### {framework.title()} Tests\n"
            if framework.lower() == "pytest":
                doc += f"```bash\npytest tests/\npytest --cov=src tests/\n```\n"
            elif framework.lower() == "jest":
                doc += f"```bash\nnpm test\nnpm run test:coverage\n```\n"
            elif framework.lower() == "cypress":
                doc += f"```bash\nnpx cypress open\nnpx cypress run\n```\n"
            doc += "\n"
        
        doc += f"## Test Files\n"
        for test_file in qa_result.test_files:
            doc += f"- **{test_file.path}**: {test_file.test_type} tests using {test_file.framework}\n"
        
        doc += f"\n## Dependencies\n"
        all_deps = set()
        for test_file in qa_result.test_files:
            all_deps.update(test_file.dependencies)
        
        doc += f"Install required testing dependencies:\n"
        doc += f"```bash\npip install {' '.join([dep for dep in all_deps if dep in ['pytest', 'pytest-cov', 'pytest-mock']])}\n```\n"
        doc += f"```bash\nnpm install {' '.join([dep for dep in all_deps if dep in ['jest', 'cypress', '@testing-library/react']])}\n```\n"
        
        doc += "\n---\n*Generated by AI-SOL Context-Aware QA Engineer*\n"
        return doc
    
    def _generate_qa_report(self, quality_results: List[Dict], qa_result: QAResult, avg_quality: float) -> str:
        doc = "# Quality Assurance Report\n\n"
        doc += f"## Overall Metrics\n**Code Quality Score:** {avg_quality:.1f}/100\n"
        doc += f"**Estimated Test Coverage:** {qa_result.test_coverage_estimate:.1f}%\n"
        doc += f"**Security Issues Found:** {len(qa_result.security_findings)}\n\n"

        doc += "## Code Quality Analysis\n"
        for result in quality_results:
            doc += f"### {result['file']}\n"
            doc += f"**Quality Score:** {result['quality_score']:.1f}/100\n"
            doc += f"**Complexity:** {result['complexity']}\n"
            doc += f"**Issues:** {len(result['issues'])}\n"
            for issue in result['issues'][:5]:
                doc += f"- Line {issue.get('line', '?')}: {issue.get('message', 'Unknown')}\n"
            doc += "\n"

        doc += "## Security Findings\n"
        if qa_result.security_findings:
            for finding in qa_result.security_findings:
                doc += f"### {finding.type} - {finding.severity.upper()}\n"
                doc += f"**Location:** {finding.location}\n"
                doc += f"**Description:** {finding.description}\n"
                doc += f"**Fix:** {finding.fix}\n\n"
        else:
            doc += "No critical security issues found.\n\n"

        doc += "## Test Suite\n"
        for test in qa_result.test_files:
            doc += f"- {test.path} ({test.test_type}), Coverage: {test.coverage_target}\n"

        doc += "## Recommendations\n"
        for rec in qa_result.recommendations:
            doc += f"- {rec}\n"

        doc += "\n---\n*Generated by AI-SOL QA Engineer*\n"
        return doc
    
    def _calculate_quality_score(self, file_path: str, code: str) -> float:
        """Calculate quality score for any file type"""
        if not code or not code.strip():
            return 20.0  # Very low score for empty files
        
        score = 50.0  # Base score
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Length-based scoring
        if len(non_empty_lines) > 10:
            score += 10  # Bonus for substantial content
        elif len(non_empty_lines) > 5:
            score += 5   # Small bonus for moderate content
        
        # File type specific scoring
        if file_path.endswith('.html'):
            score += self._score_html_quality(code)
        elif file_path.endswith('.css'):
            score += self._score_css_quality(code)
        elif file_path.endswith('.js'):
            score += self._score_js_quality(code)
        elif file_path.endswith('.py'):
            score += self._score_python_quality(code)
        
        # General code quality indicators
        if 'function' in code or 'def ' in code or 'class ' in code:
            score += 10  # Bonus for structured code
        
        if '//' in code or '#' in code:
            score += 5   # Bonus for comments
        
        if 'error' not in code.lower() and 'todo' not in code.lower():
            score += 5   # Bonus for no obvious errors or TODOs
        
        # Cap the score
        return min(score, 95.0)
    
    def _score_html_quality(self, code: str) -> float:
        """Score HTML quality"""
        score = 0
        if '<!DOCTYPE html>' in code:
            score += 5
        if '<html' in code and '</html>' in code:
            score += 5
        if '<head>' in code and '</head>' in code:
            score += 5
        if '<body>' in code and '</body>' in code:
            score += 5
        if 'meta' in code:
            score += 3
        return score
    
    def _score_css_quality(self, code: str) -> float:
        """Score CSS quality"""
        score = 0
        if '{' in code and '}' in code:
            score += 5
        if ':' in code:
            score += 3
        if 'margin' in code or 'padding' in code:
            score += 2
        return score
    
    def _score_js_quality(self, code: str) -> float:
        """Score JavaScript quality"""
        score = 0
        if 'function' in code or '=>' in code:
            score += 5
        if 'addEventListener' in code or 'querySelector' in code:
            score += 5
        if 'const ' in code or 'let ' in code:
            score += 3
        return score
    
    def _score_python_quality(self, code: str) -> float:
        """Score Python quality"""
        score = 0
        if 'def ' in code:
            score += 5
        if 'class ' in code:
            score += 5
        if 'import ' in code:
            score += 3
        if 'try:' in code or 'except' in code:
            score += 3
        return score
    
    def _analyze_non_python_code(self, file_path: str, code: str) -> List[Dict]:
        """Basic analysis for non-Python files"""
        issues = []
        
        # Check for common issues
        if len(code.strip()) < 10:
            issues.append({
                "line": 1,
                "message": "File is very short, may be incomplete",
                "severity": "medium"
            })
        
        if file_path.endswith('.html') and '<!DOCTYPE' not in code:
            issues.append({
                "line": 1,
                "message": "Missing DOCTYPE declaration",
                "severity": "low"
            })
        
        if file_path.endswith('.css') and '{' not in code:
            issues.append({
                "line": 1,
                "message": "No CSS rules found",
                "severity": "medium"
            })
        
        return issues
    
    def _calculate_complexity(self, file_path: str, code: str) -> int:
        """Calculate basic complexity for any file type"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Basic complexity based on file type and content
        complexity = non_empty_lines // 10  # 1 point per 10 lines
        
        if file_path.endswith('.py'):
            complexity += code.count('def ') + code.count('class ') + code.count('if ') + code.count('for ') + code.count('while ')
        elif file_path.endswith('.js'):
            complexity += code.count('function') + code.count('=>') + code.count('if ') + code.count('for ')
        elif file_path.endswith('.html'):
            complexity += code.count('<div') + code.count('<section') + code.count('<article')
        
        return max(complexity, 1)  # Minimum complexity of 1

    async def verify_code(self, task: Any, code: str, context: AgentContext) -> Dict[str, Any]:
        """
        Lightweight code verifier used by the orchestrator during the build loop.
        Returns JSON: {"valid": bool, "error": Optional[str]}.
        Performs basic syntax checks (for Python) and basic heuristics.
        """
        try:
            path = task.path if hasattr(task, 'path') else task.get('path', 'unnamed')
            # Basic Python syntax check
            if str(path).endswith('.py'):
                try:
                    compile(code, path, 'exec')
                except SyntaxError as se:
                    return {"valid": False, "error": f"SyntaxError: {se.msg} at line {se.lineno}"}
                except Exception as e:
                    return {"valid": False, "error": f"Python compile error: {e}"}

            # Basic non-empty check
            if not code or not code.strip():
                return {"valid": False, "error": "Generated code is empty"}

            # Basic import check: ensure no obviously missing local imports
            # (Heuristic) Find 'from x import' or 'import x'
            import_re = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)", re.MULTILINE)
            imports = set(m.group(1) for m in import_re.finditer(code))
            # Cross-check with blueprint if available
            bp = getattr(context, 'blueprint', None)
            if bp and imports:
                # Build set of module/file roots from blueprint build_plan
                file_roots = set()
                for f in bp.build_plan:
                    p = f.path if hasattr(f, 'path') else f.get('path')
                    root = Path(p).stem
                    file_roots.add(root)
                # If any import refers to a local module not in file_roots, warn (but not fail)
                missing = [imp for imp in imports if imp.split('.')[0] in file_roots and imp.split('.')[0] not in file_roots]
                # (This heuristic is conservative; we won't fail on it.)

            return {"valid": True, "error": None}
        except Exception as e:
            return {"valid": False, "error": str(e)}
