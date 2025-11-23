#!/usr/bin/env python3
"""
Fix requirements.py broken methods
"""

file_path = r'd:\AI\AIML\SUNRISE COUNTDOWN\ai-craftsman-portfolio\projects\AI-SOL\agents\requirements.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the broken section
fixed_lines = []
skip_until = None

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Skip the broken section (lines 394-403)
    if line_num == 394:
        # Insert the correct closing and missing methods
        fixed_lines.append('                    "database": ["PostgreSQL", "MongoDB"],\n')
        fixed_lines.append('                    "infrastructure": ["AWS", "Docker", "Kubernetes"]\n')
        fixed_lines.append('                }\n')
        fixed_lines.append('            }\n')
        fixed_lines.append('        }\n')
        fixed_lines.append('\n')
        fixed_lines.append('    async def _conduct_domain_research(self, requirements: str, classification, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:\n')
        fixed_lines.append('        """Conduct domain-specific research"""\n')
        fixed_lines.append('        research_results = []\n')
        fixed_lines.append('\n')
        fixed_lines.append('        if not user_context.get("enable_research", True):\n')
        fixed_lines.append('            return research_results\n')
        fixed_lines.append('\n')
        fixed_lines.append('        try:\n')
        fixed_lines.append('            domain = classification.domain\n')
        fixed_lines.append('            project_type = classification.project_type.value\n')
        fixed_lines.append('\n')
        fixed_lines.append('            search_queries = [\n')
        fixed_lines.append('                f"best practices {domain} {project_type} development",\n')
        fixed_lines.append('                f"{domain} software requirements standards",\n')
        fixed_lines.append('                f"{project_type} architecture patterns {domain}"\n')
        fixed_lines.append('            ]\n')
        fixed_lines.append('\n')
        fixed_lines.append('            for query in search_queries:\n')
        fixed_lines.append('                self.log(f"Researching: {query}", "info")\n')
        fixed_lines.append('                search_result = self.call_tool("web_search", query=query, max_results=2)\n')
        fixed_lines.append('\n')
        fixed_lines.append('                if search_result.get("success"):\n')
        fixed_lines.append('                    results = search_result.get("results", [])\n')
        fixed_lines.append('                    research_results.extend(results)\n')
        fixed_lines.append('\n')
        fixed_lines.append('            self.log(f"Domain research completed: {len(research_results)} results found", "info")\n')
        fixed_lines.append('\n')
        fixed_lines.append('        except Exception as e:\n')
        fixed_lines.append('            self.log(f"Research failed: {e}", "warning")\n')
        fixed_lines.append('\n')
        fixed_lines.append('        return research_results\n')
        fixed_lines.append('\n')
        fixed_lines.append('    def _format_domain_context(self, classification, domain_template: Dict[str, Any], research_results: List[Dict[str, Any]]) -> str:\n')
        fixed_lines.append('        """Format domain-specific context for prompt"""\n')
        fixed_lines.append('        context = f"Domain: {classification.domain}\\n"\n')
        fixed_lines.append('        context += f"Project Type: {classification.project_type.value}\\n"\n')
        fixed_lines.append('\n')
        fixed_lines.append('        if domain_template:\n')
        fixed_lines.append('            context += "\\n**Domain-Specific Patterns:**\\n"\n')
        fixed_lines.append('\n')
        fixed_lines.append('            if "functional_patterns" in domain_template:\n')
        fixed_lines.append('                context += "Common Functional Requirements:\\n"\n')
        fixed_lines.append('                for pattern in domain_template["functional_patterns"]:\n')
        fixed_lines.append('                    context += f"- {pattern}\\n"\n')
        fixed_lines.append('\n')
        fixed_lines.append('            if "non_functional_patterns" in domain_template:\n')
        fixed_lines.append('                context += "\\nCommon Non-Functional Requirements:\\n"\n')
        fixed_lines.append('                for pattern in domain_template["non_functional_patterns"]:\n')
        fixed_lines.append('                    context += f"- {pattern[\\"category\\"]}: {pattern[\\"description\\"]}\\n"\n')
        fixed_lines.append('\n')
        fixed_lines.append('            if "tech_recommendations" in domain_template:\n')
        fixed_lines.append('                context += "\\nRecommended Technologies:\\n"\n')
        fixed_lines.append('                for category, techs in domain_template["tech_recommendations"].items():\n')
        fixed_lines.append('                    context += f"- {category}: {\\", \\".join(techs)}\\n"\n')
        fixed_lines.append('\n')
        fixed_lines.append('        return context\n')
        fixed_lines.append('\n')
        fixed_lines.append('    def _format_research_results(self, research_results: List[Dict[str, Any]]) -> str:\n')
       fixed_lines.append('        """Format research results for prompt"""\n')
        fixed_lines.append('        if not research_results:\n')
        skip_until = 404  # Skip to line 404
        continue
    
    if skip_until and line_num < skip_until:
        continue
    
    if skip_until and line_num == skip_until:
        skip_until = None
    
    fixed_lines.append(line)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print('Successfully fixed requirements.py')
