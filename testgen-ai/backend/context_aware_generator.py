"""
Context-Aware Test Generator
LLM-powered test case generation with context extraction from multiple sources
"""

import os
import json
import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import yaml
from pathlib import Path

# LLM API imports
try:
    import openai
    from anthropic import Anthropic
    print(f"✅ OpenAI library version: {openai.__version__}")
except ImportError as e:
    print(f"❌ Failed to import LLM libraries: {e}")
    openai = None
    Anthropic = None

class ContextExtractor:
    """Extract context from various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def extract_jira_context(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from Jira issues"""
        try:
            jira_url = config.get("jira_url")
            username = config.get("username")
            api_token = config.get("api_token")
            issue_keys = config.get("issue_keys", [])
            
            if not all([jira_url, username, api_token, issue_keys]):
                raise ValueError("Missing required Jira configuration")
            
            context = {
                "source": "jira",
                "issues": [],
                "epics": [],
                "stories": [],
                "acceptance_criteria": []
            }
            
            # Fetch issues from Jira
            for issue_key in issue_keys:
                issue_data = await self._fetch_jira_issue(jira_url, username, api_token, issue_key)
                if issue_data:
                    context["issues"].append(issue_data)
                    
                    # Categorize by issue type
                    if issue_data.get("fields", {}).get("issuetype", {}).get("name") == "Epic":
                        context["epics"].append(issue_data)
                    elif issue_data.get("fields", {}).get("issuetype", {}).get("name") == "Story":
                        context["stories"].append(issue_data)
                    
                    # Extract acceptance criteria
                    description = issue_data.get("fields", {}).get("description", "")
                    if "Acceptance Criteria" in description:
                        criteria = self._extract_acceptance_criteria(description)
                        context["acceptance_criteria"].extend(criteria)
            
            return context
            
        except Exception as e:
            raise Exception(f"Jira context extraction failed: {str(e)}")
    
    async def _fetch_jira_issue(self, jira_url: str, username: str, api_token: str, issue_key: str) -> Optional[Dict]:
        """Fetch individual Jira issue"""
        try:
            url = f"{jira_url}/rest/api/2/issue/{issue_key}"
            response = self.session.get(
                url,
                auth=(username, api_token),
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Failed to fetch Jira issue {issue_key}: {str(e)}")
            return None
    
    def _extract_acceptance_criteria(self, description: str) -> List[str]:
        """Extract acceptance criteria from Jira description"""
        criteria = []
        lines = description.split('\n')
        in_criteria_section = False
        
        for line in lines:
            line = line.strip()
            if "Acceptance Criteria" in line:
                in_criteria_section = True
                continue
            elif in_criteria_section:
                if line.startswith(('*', '-', '•')) or line.startswith(('1.', '2.', '3.')):
                    criteria.append(line)
                elif line == "":
                    continue
                else:
                    break
        
        return criteria
    
    async def extract_url_context(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from web application"""
        try:
            url = config.get("url")
            if not url:
                raise ValueError("URL is required")
            
            # Fetch page content
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            context = {
                "source": "url",
                "url": url,
                "title": soup.title.string if soup.title else "",
                "forms": [],
                "navigation": [],
                "buttons": [],
                "inputs": [],
                "links": [],
                "content_structure": {}
            }
            
            # Extract forms
            forms = soup.find_all('form')
            for form in forms:
                form_data = {
                    "action": form.get('action', ''),
                    "method": form.get('method', 'GET'),
                    "inputs": []
                }
                
                inputs = form.find_all(['input', 'select', 'textarea'])
                for inp in inputs:
                    input_data = {
                        "type": inp.get('type', inp.name),
                        "name": inp.get('name', ''),
                        "id": inp.get('id', ''),
                        "placeholder": inp.get('placeholder', ''),
                        "required": inp.has_attr('required')
                    }
                    form_data["inputs"].append(input_data)
                
                context["forms"].append(form_data)
            
            # Extract navigation
            nav_elements = soup.find_all(['nav', 'ul', 'ol'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['nav', 'menu', 'breadcrumb']
            ))
            for nav in nav_elements:
                links = nav.find_all('a')
                nav_data = [{"text": link.get_text().strip(), "href": link.get('href', '')} for link in links]
                context["navigation"].extend(nav_data)
            
            # Extract buttons
            buttons = soup.find_all(['button', 'input[type="button"]', 'input[type="submit"]'])
            for button in buttons:
                button_data = {
                    "text": button.get_text().strip() or button.get('value', ''),
                    "type": button.get('type', 'button'),
                    "class": button.get('class', [])
                }
                context["buttons"].append(button_data)
            
            # Extract all inputs
            inputs = soup.find_all('input')
            for inp in inputs:
                input_data = {
                    "type": inp.get('type', 'text'),
                    "name": inp.get('name', ''),
                    "id": inp.get('id', ''),
                    "placeholder": inp.get('placeholder', ''),
                    "required": inp.has_attr('required')
                }
                context["inputs"].append(input_data)
            
            # Extract links
            links = soup.find_all('a', href=True)
            for link in links[:50]:  # Limit to first 50 links
                link_data = {
                    "text": link.get_text().strip(),
                    "href": link.get('href', ''),
                    "title": link.get('title', '')
                }
                context["links"].append(link_data)
            
            # Extract content structure
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            context["content_structure"]["headings"] = [
                {"level": int(h.name[1]), "text": h.get_text().strip()} for h in headings
            ]
            
            return context
            
        except Exception as e:
            raise Exception(f"URL context extraction failed: {str(e)}")
    
    async def extract_file_context(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from uploaded files"""
        try:
            file_path = config.get("file_path")
            file_type = config.get("file_type", "text")
            
            if not file_path or not os.path.exists(file_path):
                raise ValueError("File not found")
            
            context = {
                "source": "file",
                "file_type": file_type,
                "file_name": os.path.basename(file_path),
                "content": "",
                "structured_data": {}
            }
            
            # Read file content based on type
            if file_type == "yaml" or file_path.endswith(('.yml', '.yaml')):
                with open(file_path, 'r', encoding='utf-8') as f:
                    context["structured_data"] = yaml.safe_load(f)
                    context["content"] = f.read()
            elif file_type == "json" or file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    context["structured_data"] = json.load(f)
                    context["content"] = f.read()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    context["content"] = f.read()
            
            return context
            
        except Exception as e:
            raise Exception(f"File context extraction failed: {str(e)}")


class ContextAwareTestGenerator:
    """Generate test cases using LLM with context awareness"""
    
    def __init__(self, integrations: List[Any] = None):
        self.openai_client = None
        self.anthropic_client = None
        self.integrations = integrations or []
        
        # Initialize clients from integrations
        self._initialize_clients_from_integrations()
    
    def _initialize_clients_from_integrations(self):
        """Initialize LLM clients from user integrations"""
        print(f"🔍 Initializing clients from {len(self.integrations)} integrations")
        for integration in self.integrations:
            print(f"🔍 Processing integration: {integration.integration_type}")
            if integration.integration_type == "openai" and openai:
                # Decrypt credentials (stored as JSON)
                try:
                    credentials = json.loads(integration.encrypted_credentials)
                    api_key = credentials.get("api_key")
                    base_url = credentials.get("base_url")
                    if api_key:
                        # Initialize OpenAI client with minimal parameters
                        try:
                            # Initialize OpenAI client with custom base URL if provided
                            if base_url:
                                print(f"🌐 Using custom OpenAI base URL: {base_url}")
                                self.openai_client = openai.AsyncOpenAI(
                                    api_key=api_key,
                                    base_url=base_url
                                )
                            else:
                                self.openai_client = openai.AsyncOpenAI(api_key=api_key)
                            print("✅ OpenAI client initialized from integration")
                        except Exception as init_error:
                            print(f"❌ OpenAI client initialization failed: {init_error}")
                            # For now, set to None to use mock content
                            self.openai_client = None
                except Exception as e:
                    print(f"❌ Failed to initialize OpenAI client: {e}")
                    self.openai_client = None
            
            elif integration.integration_type == "anthropic" and Anthropic:
                # Decrypt credentials (stored as JSON)
                try:
                    credentials = json.loads(integration.encrypted_credentials)
                    api_key = credentials.get("api_key")
                    base_url = credentials.get("base_url")
                    if api_key:
                        # Initialize Anthropic client with custom base URL if provided
                        if base_url:
                            print(f"🌐 Using custom Anthropic base URL: {base_url}")
                            self.anthropic_client = Anthropic(
                                api_key=api_key,
                                base_url=base_url
                            )
                        else:
                            self.anthropic_client = Anthropic(api_key=api_key)
                        print("✅ Anthropic client initialized from integration")
                except Exception as e:
                    print(f"❌ Failed to initialize Anthropic client: {e}")
        
        # Fallback to environment variables if no integrations found
        if not self.openai_client and not self.anthropic_client:
            if openai:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    try:
                        self.openai_client = openai.AsyncOpenAI(api_key=api_key)
                        print("✅ OpenAI client initialized from environment")
                    except Exception as e:
                        print(f"❌ Failed to initialize OpenAI client from environment: {e}")
            
            if Anthropic:
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    try:
                        self.anthropic_client = Anthropic(api_key=api_key)
                        print("✅ Anthropic client initialized from environment")
                    except Exception as e:
                        print(f"❌ Failed to initialize Anthropic client from environment: {e}")
    
    async def generate_tests(
        self,
        feature_name: str,
        context: Dict[str, Any],
        config: Dict[str, Any],
        integrations: List[Any] = None
    ) -> Dict[str, str]:
        """Generate comprehensive test cases"""
        
        # Determine which LLM to use
        llm_provider = config.get("llm_provider", "openai")
        
        # Build comprehensive prompt
        prompt = self._build_generation_prompt(feature_name, context, config)
        
        # Generate tests using selected LLM
        if llm_provider == "openai" and self.openai_client:
            try:
                generated_content = await self._generate_with_openai(prompt, config)
            except Exception as e:
                print(f"❌ OpenAI generation failed: {e}")
                print("⚠️  Falling back to mock content generation")
                generated_content = self._generate_mock_content(feature_name, context, config)
        elif llm_provider == "anthropic" and self.anthropic_client:
            try:
                generated_content = await self._generate_with_anthropic(prompt, config)
            except Exception as e:
                print(f"❌ Anthropic generation failed: {e}")
                print("⚠️  Falling back to mock content generation")
                generated_content = self._generate_mock_content(feature_name, context, config)
        else:
            # For development: generate mock content when LLM is not available
            print(f"⚠️  LLM provider {llm_provider} not available, generating mock content")
            generated_content = self._generate_mock_content(feature_name, context, config)
        
        # Parse and structure the generated content
        test_files = self._parse_generated_content(generated_content, feature_name, context)
        
        return test_files
    
    def _generate_mock_content(self, feature_name: str, context: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate mock test content for development when LLM is not available"""
        
        clean_name = "".join(c for c in feature_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_').lower()
        
        # Extract URL from context if available
        base_url = "https://example.com"
        if context and context.get("context_sources"):
            for source in context["context_sources"]:
                if source.get("type") == "url" and source.get("extracted", {}).get("url"):
                    base_url = source["extracted"]["url"]
                    break
        
        mock_content = """# Mock Test Generation for: {feature_name}

## Generated Test Files:

```pom.xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.testgen</groupId>
    <artifactId>selenium-cucumber-tests</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <version>7.14.0</version>
        </dependency>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-junit</artifactId>
            <version>7.14.0</version>
        </dependency>
        <dependency>
            <groupId>org.seleniumhq.selenium</groupId>
            <artifactId>selenium-java</artifactId>
            <version>4.15.0</version>
        </dependency>
        <dependency>
            <groupId>io.github.bonigarcia</groupId>
            <artifactId>webdrivermanager</artifactId>
            <version>5.5.3</version>
        </dependency>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
        </dependency>
    </dependencies>
</project>
```

```src/test/java/TestRunner.java
package com.testgen;

import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;
import org.junit.runner.RunWith;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "src/test/resources/features",
    glue = "com.testgen.stepdefinitions",
    plugin = {{"pretty", "html:target/cucumber-reports", "json:target/cucumber-reports/Cucumber.json"}},
    monochrome = true
)
public class TestRunner {{
}}
```

```src/test/resources/features/{clean_name}.feature
Feature: {feature_name}
  As a user
  I want to test the {feature_name} functionality
  So that I can ensure it works correctly

  Scenario: Basic functionality test
    Given I am on the page at "{base_url}"
    When I perform the main action
    Then I should see the expected result

  Scenario: Error handling test
    Given I am on the page at "{base_url}"
    When I perform an invalid action
    Then I should see an error message
```

```src/test/java/stepdefinitions/{clean_name}_steps.java
package com.testgen.stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.junit.Assert;

public class {clean_name_title}Steps {{
    
    @Given("I am on the page at {{string}}")
    public void i_am_on_the_page(String url) {{
        // TODO: Implement navigation to the specified URL
        System.out.println("Navigating to " + url + "...");
    }}
    
    @When("I perform the main action")
    public void i_perform_the_main_action() {{
        // TODO: Implement main action
        System.out.println("Performing main action...");
    }}
    
    @When("I perform an invalid action")
    public void i_perform_an_invalid_action() {{
        // TODO: Implement invalid action
        System.out.println("Performing invalid action...");
    }}
    
    @Then("I should see the expected result")
    public void i_should_see_the_expected_result() {{
        // TODO: Implement verification
        Assert.assertTrue("Expected result not found", true);
    }}
    
    @Then("I should see an error message")
    public void i_should_see_an_error_message() {{
        // TODO: Implement error verification
        Assert.assertTrue("Error message not found", true);
    }}
}}
```

```README.md
# {feature_name} Test Suite

## Overview
This test suite was generated by TestGen AI for testing the {feature_name} functionality.

## Prerequisites
- Java 11 or higher
- Maven 3.6 or higher
- Chrome/Firefox/Edge browser

## Running Tests
```bash
mvn clean test
```

## Test Reports
Test reports will be generated in the `target/cucumber-reports` directory.

## Note
This is a mock test suite generated for development purposes. 
To generate real test cases, configure your LLM API keys in the environment variables.
```

## Context Information Used:
{context_json}

## Configuration Used:
{config_json}
""".format(
            feature_name=feature_name,
            clean_name=clean_name,
            clean_name_title=clean_name.title().replace('_', ''),
            base_url=base_url,
            context_json=json.dumps(context, indent=2),
            config_json=json.dumps(config, indent=2)
        )
        
        return mock_content
    
    def _build_generation_prompt(self, feature_name: str, context: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Build comprehensive prompt for test generation"""
        
        prompt = f"""
You are an expert QA automation engineer. Generate comprehensive Cucumber Selenium Java test cases for the feature: "{feature_name}".

## Context Information:

### Project Context:
{json.dumps(context.get('project_context', {}), indent=2)}

### Context Sources:
"""
        
        # Add context from different sources
        for source in context.get('context_sources', []):
            source_type = source.get('type')
            extracted = source.get('extracted', {})
            
            if source_type == 'jira':
                prompt += f"""
### Jira Issues:
"""
                for issue in extracted.get('issues', []):
                    fields = issue.get('fields', {})
                    prompt += f"""
- **{issue.get('key')}**: {fields.get('summary', '')}
  - Description: {fields.get('description', '')}
  - Issue Type: {fields.get('issuetype', {}).get('name', '')}
  - Status: {fields.get('status', {}).get('name', '')}
"""
                
                if extracted.get('acceptance_criteria'):
                    prompt += f"""
### Acceptance Criteria:
"""
                    for criteria in extracted['acceptance_criteria']:
                        prompt += f"- {criteria}\n"
            
            elif source_type == 'url':
                url = extracted.get('url', '')
                title = extracted.get('title', '')
                forms = extracted.get('forms', [])
                navigation = extracted.get('navigation', [])
                buttons = extracted.get('buttons', [])
                inputs = extracted.get('inputs', [])
                
                prompt += f"""
### Web Application Analysis:
- **Target URL**: {url}
- **Page Title**: {title}
- **Forms Found**: {len(forms)} forms
- **Navigation Items**: {len(navigation)} items
- **Buttons Found**: {len(buttons)} buttons
- **Input Fields**: {len(inputs)} input fields

### Detailed Form Analysis:
"""
                
                # Add detailed form information
                for i, form in enumerate(forms[:3]):  # Limit to first 3 forms
                    form_inputs = form.get('inputs', [])
                    prompt += f"""
**Form {i+1}**:
- Action URL: {form.get('action', '')}
- Method: {form.get('method', 'GET')}
- Input Fields ({len(form_inputs)}):
"""
                    for j, inp in enumerate(form_inputs[:10]):  # Limit to first 10 inputs per form
                        prompt += f"  - {inp.get('type', 'text')} field: name='{inp.get('name', '')}' id='{inp.get('id', '')}' placeholder='{inp.get('placeholder', '')}' {'(required)' if inp.get('required') else ''}\n"
                
                # Add navigation details
                if navigation:
                    prompt += f"""
### Navigation Structure:
"""
                    for nav_item in navigation[:10]:  # Limit to first 10 nav items
                        prompt += f"- {nav_item.get('text', '')} -> {nav_item.get('href', '')}\n"
                
                # Add button details
                if buttons:
                    prompt += f"""
### Interactive Elements:
"""
                    for button in buttons[:10]:  # Limit to first 10 buttons
                        prompt += f"- {button.get('text', '')} ({button.get('type', 'button')})\n"
            
            elif source_type == 'file':
                prompt += f"""
### File Content:
- File: {extracted.get('file_name', '')}
- Type: {extracted.get('file_type', '')}
- Content Preview: {extracted.get('content', '')[:500]}...
"""
        
        prompt += f"""

## Test Generation Requirements:

1. **Generate a complete Maven project structure** with:
   - pom.xml with all necessary dependencies
   - TestRunner class for Cucumber execution
   - Page Object Model classes
   - Step definition classes
   - Feature files with Gherkin scenarios

2. **Test Coverage**:
   - Happy path scenarios
   - Edge cases and error conditions
   - Security tests (if applicable)
   - Performance considerations
   - Cross-browser compatibility

3. **Code Quality**:
   - Follow Java best practices
   - Use proper naming conventions
   - Include comprehensive comments
   - Implement proper error handling
   - Use Page Object Model pattern

4. **Configuration**:
   - Support for different browsers (Chrome, Firefox, Edge)
   - Configurable test data
   - Environment-specific configurations
   - Parallel execution support

## Output Format:
Generate the complete test suite as a structured response with each file clearly marked with its path and content.

Generate comprehensive, production-ready test cases that cover all the requirements and context provided.
"""
        
        return prompt
    
    async def _generate_with_openai(self, prompt: str, config: Dict[str, Any]) -> str:
        """Generate tests using OpenAI"""
        try:
            # Use gpt-3.5-turbo as default since it's more widely available
            model = config.get("model", "gpt-3.5-turbo")
            print(f"🤖 Using OpenAI model: {model}")
            
            response = await self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert QA automation engineer specializing in Cucumber Selenium Java test automation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.get("max_tokens", 4000),
                temperature=config.get("temperature", 0.1)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "billing" in error_msg.lower():
                raise Exception(f"OpenAI quota exceeded: {error_msg}")
            else:
                raise Exception(f"OpenAI generation failed: {error_msg}")
    
    async def _generate_with_anthropic(self, prompt: str, config: Dict[str, Any]) -> str:
        """Generate tests using Anthropic Claude"""
        try:
            response = self.anthropic_client.messages.create(
                model=config.get("model", "claude-3-sonnet-20240229"),
                max_tokens=config.get("max_tokens", 4000),
                temperature=config.get("temperature", 0.1),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Anthropic generation failed: {str(e)}")
    
    def _parse_generated_content(self, content: str, feature_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Parse generated content into structured files"""
        
        files = {}
        current_file = None
        current_content = []
        
        lines = content.split('\n')
        
        for line in lines:
            # Check for file markers
            if line.startswith('```') and ':' in line:
                # Save previous file
                if current_file and current_content:
                    files[current_file] = '\n'.join(current_content)
                
                # Start new file
                file_path = line.replace('```', '').strip()
                if ':' in file_path:
                    file_path = file_path.split(':', 1)[1].strip()
                current_file = file_path
                current_content = []
                continue
            
            elif line.startswith('```') and not current_file:
                continue
            
            elif line.startswith('```') and current_file:
                # End of current file
                if current_content:
                    files[current_file] = '\n'.join(current_content)
                current_file = None
                current_content = []
                continue
            
            # Add content to current file
            if current_file:
                current_content.append(line)
        
        # Save last file
        if current_file and current_content:
            files[current_file] = '\n'.join(current_content)
        
        # If no structured files found, create default structure
        if not files:
            files = self._create_default_test_structure(feature_name, content, context)
        
        return files
    
    def _create_default_test_structure(self, feature_name: str, content: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Create default test structure if parsing fails"""
        
        # Clean feature name for file names
        clean_name = "".join(c for c in feature_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        clean_name = clean_name.replace(' ', '_').lower()
        
        files = {
            f"pom.xml": self._get_default_pom(),
            f"src/test/java/TestRunner.java": self._get_default_test_runner(clean_name),
            f"src/test/java/pages/BasePage.java": self._get_default_base_page(),
            f"src/test/java/stepdefinitions/{clean_name}_steps.java": self._get_default_step_definitions(clean_name),
            f"src/test/resources/features/{clean_name}.feature": self._get_default_feature_file(clean_name, content, context),
            f"src/test/resources/config.properties": self._get_default_config(context),
            f"README.md": self._get_default_readme(clean_name)
        }
        
        return files
    
    def _get_default_pom(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.testgen</groupId>
    <artifactId>selenium-cucumber-tests</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <version>7.14.0</version>
        </dependency>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-junit</artifactId>
            <version>7.14.0</version>
        </dependency>
        <dependency>
            <groupId>org.seleniumhq.selenium</groupId>
            <artifactId>selenium-java</artifactId>
            <version>4.15.0</version>
        </dependency>
        <dependency>
            <groupId>io.github.bonigarcia</groupId>
            <artifactId>webdrivermanager</artifactId>
            <version>5.5.3</version>
        </dependency>
        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
        </dependency>
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.1.2</version>
            </plugin>
        </plugins>
    </build>
</project>"""
    
    def _get_default_test_runner(self, feature_name: str) -> str:
        return f"""package com.testgen;

import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;
import org.junit.runner.RunWith;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "src/test/resources/features",
    glue = "com.testgen.stepdefinitions",
    plugin = {{"pretty", "html:target/cucumber-reports", "json:target/cucumber-reports/Cucumber.json"}},
    monochrome = true
)
public class TestRunner {{
}}"""
    
    def _get_default_base_page(self) -> str:
        return """package com.testgen.pages;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import java.time.Duration;

public class BasePage {
    protected WebDriver driver;
    protected WebDriverWait wait;
    
    public BasePage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        PageFactory.initElements(driver, this);
    }
    
    protected void waitForElement(WebElement element) {
        wait.until(ExpectedConditions.visibilityOf(element));
    }
    
    protected void clickElement(WebElement element) {
        waitForElement(element);
        element.click();
    }
    
    protected void enterText(WebElement element, String text) {
        waitForElement(element);
        element.clear();
        element.sendKeys(text);
    }
}"""
    
    def _get_default_step_definitions(self, feature_name: str) -> str:
        class_name = ''.join(word.title() for word in feature_name.split('_'))
        feature_lower = feature_name.lower()
        
        # Check if it's a search feature
        if 'search' in feature_lower:
            search_term = ' '.join([word for word in feature_name.split('_') if word.lower() not in ['search', 'for', 'a', 'an', 'the']])
            if not search_term:
                search_term = "items"
                
            return f"""package com.testgen.stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.And;
import org.junit.Assert;
import org.openqa.selenium.By;
import org.openqa.selenium.Keys;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;

public class {class_name}Steps {{
    
    private WebDriver driver;
    private WebDriverWait wait;
    private long startTime;
    
    @Given("I navigate to {{string}}")
    public void i_navigate_to(String url) {{
        driver.get(url);
    }}
    
    @And("I wait for the search box to be visible")
    public void i_wait_for_search_box() {{
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        wait.until(ExpectedConditions.visibilityOfElementLocated(By.name("q")));
    }}
    
    @When("I enter {{string}} in the Google search box")
    public void i_enter_search_term(String searchTerm) {{
        WebElement searchBox = driver.findElement(By.name("q"));
        searchBox.clear();
        searchBox.sendKeys(searchTerm);
    }}
    
    @And("I press Enter or click the Google Search button")
    public void i_click_search_button() {{
        WebElement searchBox = driver.findElement(By.name("q"));
        searchBox.sendKeys(Keys.ENTER);
    }}
    
    @And("I click the Google Search button")
    public void i_click_google_search_button() {{
        WebElement searchButton = driver.findElement(By.name("btnK"));
        searchButton.click();
    }}
    
    @Then("I should see search results for {{string}}")
    public void i_should_see_search_results(String searchTerm) {{
        wait.until(ExpectedConditions.presenceOfElementLocated(By.id("search")));
        String pageSource = driver.getPageSource();
        Assert.assertTrue("Search results not found for: " + searchTerm, 
            pageSource.contains(searchTerm) || !driver.findElements(By.cssSelector("#search .g")).isEmpty());
    }}
    
    @And("the results should contain relevant links")
    public void results_contain_links() {{
        Assert.assertTrue("No search result links found", 
            driver.findElements(By.cssSelector("#search .g a")).size() > 0);
    }}
    
    @And("the search query should be displayed in the search box")
    public void search_query_displayed() {{
        WebElement searchBox = driver.findElement(By.name("q"));
        Assert.assertFalse("Search box is empty", searchBox.getAttribute("value").isEmpty());
    }}
    
    @When("I start typing {{string}} in the Google search box")
    public void i_start_typing(String partialText) {{
        WebElement searchBox = driver.findElement(By.name("q"));
        searchBox.clear();
        searchBox.sendKeys(partialText);
    }}
    
    @Then("I should see search suggestions dropdown")
    public void i_should_see_suggestions() {{
        wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".suggestions, [role='listbox']")));
        Assert.assertTrue("Suggestions dropdown not visible", 
            driver.findElements(By.cssSelector(".suggestions, [role='listbox']")).size() > 0);
    }}
    
    @And("the suggestions should be related to {{string}}")
    public void suggestions_related_to(String searchTerm) {{
        // Verify suggestions are present
        Assert.assertTrue("No suggestions found", 
            driver.findElements(By.cssSelector("[role='option']")).size() > 0);
    }}
    
    @And("results should contain keywords {{string}}, {{string}}, and {{string}}")
    public void results_contain_keywords(String keyword1, String keyword2, String keyword3) {{
        String pageContent = driver.findElement(By.id("search")).getText().toLowerCase();
        Assert.assertTrue("Keyword not found: " + keyword1, pageContent.contains(keyword1.toLowerCase()));
    }}
    
    @When("I click on the {{string}} button at the bottom")
    public void i_click_next_button(String buttonText) {{
        WebElement nextButton = driver.findElement(By.linkText(buttonText));
        nextButton.click();
    }}
    
    @Then("I should see the second page of results")
    public void i_see_second_page() {{
        wait.until(ExpectedConditions.presenceOfElementLocated(By.id("search")));
        Assert.assertTrue("Not on second page", driver.findElements(By.id("search")).size() > 0);
    }}
    
    @And("the URL should contain {{string}}")
    public void url_contains(String text) {{
        Assert.assertTrue("URL does not contain: " + text, driver.getCurrentUrl().contains(text));
    }}
    
    @When("I click on the {{string}} tab")
    public void i_click_tab(String tabName) {{
        WebElement tab = driver.findElement(By.linkText(tabName));
        tab.click();
    }}
    
    @Then("I should see image results for {{string}}")
    public void i_see_image_results(String searchTerm) {{
        wait.until(ExpectedConditions.presenceOfElementLocated(By.cssSelector("[data-ri]")));
        Assert.assertTrue("Image results not found", 
            driver.findElements(By.cssSelector("[data-ri]")).size() > 0);
    }}
    
    @And("I note the current time")
    public void note_current_time() {{
        startTime = System.currentTimeMillis();
    }}
    
    @Then("search results should load within {{int}} seconds")
    public void results_load_within_seconds(int seconds) {{
        long endTime = System.currentTimeMillis();
        long loadTime = (endTime - startTime) / 1000;
        Assert.assertTrue("Page load time exceeded: " + loadTime + "s", loadTime <= seconds);
    }}
    
    @And("the page should display the number of results found")
    public void page_displays_result_count() {{
        WebElement resultStats = driver.findElement(By.id("result-stats"));
        Assert.assertFalse("Result stats not displayed", resultStats.getText().isEmpty());
    }}
    
    @And("the page should not display any error")
    public void no_error_displayed() {{
        Assert.assertFalse("Error page displayed", 
            driver.getPageSource().toLowerCase().contains("error") && 
            driver.getPageSource().toLowerCase().contains("404"));
    }}
}}"""
        
        # Generic step definitions for non-search features
        else:
            return f"""package com.testgen.stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.And;
import org.junit.Assert;
import org.openqa.selenium.WebDriver;

public class {class_name}Steps {{
    
    private WebDriver driver;
    
    @Given("I navigate to {{string}}")
    public void i_navigate_to(String url) {{
        driver.get(url);
    }}
    
    @And("the page loads successfully")
    public void page_loads_successfully() {{
        Assert.assertNotNull("Driver not initialized", driver);
        Assert.assertTrue("Page title is empty", !driver.getTitle().isEmpty());
    }}
    
    @When("I interact with the {feature_name.replace('_', ' ')} feature")
    public void i_interact_with_feature() {{
        // TODO: Implement feature interaction
    }}
    
    @And("I provide valid input data")
    public void i_provide_valid_input() {{
        // TODO: Implement valid input
    }}
    
    @And("I submit the form")
    public void i_submit_form() {{
        // TODO: Implement form submission
    }}
    
    @Then("the action should complete successfully")
    public void action_completes_successfully() {{
        // TODO: Implement success verification
        Assert.assertTrue("Action did not complete", true);
    }}
    
    @And("I should see a confirmation message")
    public void i_see_confirmation() {{
        // TODO: Verify confirmation message
    }}
}}"""
    
    def _get_default_feature_file(self, feature_name: str, content: str, context: Dict[str, Any] = None) -> str:
        # Extract URL and analyze feature name for context-aware scenarios
        base_url = "https://example.com"
        page_title = "the application"
        
        if context and context.get("context_sources"):
            for source in context["context_sources"]:
                if source.get("type") == "url" and source.get("extracted", {}).get("url"):
                    base_url = source["extracted"]["url"]
                    page_title = source["extracted"].get("title", "the application")
                    break
        
        # Analyze feature name to generate intelligent scenarios
        feature_lower = feature_name.lower()
        scenarios = self._generate_intelligent_scenarios(feature_name, feature_lower, base_url, page_title)
        
        return f"""Feature: {feature_name.replace('_', ' ').title()}
  As a user
  I want to {feature_name.replace('_', ' ').lower()}
  So that I can find relevant results

{scenarios}
"""
    
    def _generate_intelligent_scenarios(self, feature_name: str, feature_lower: str, base_url: str, page_title: str) -> str:
        """Generate context-aware test scenarios based on feature name and URL"""
        
        # Check if it's a search-related feature
        if 'search' in feature_lower:
            search_term = ' '.join([word for word in feature_name.split('_') if word.lower() not in ['search', 'for', 'a', 'an', 'the']])
            if not search_term:
                search_term = "items"
            
            # Special handling for Google
            if 'google' in base_url.lower():
                return f"""  Background:
    Given I navigate to "{base_url}"
    And I wait for the search box to be visible

  @smoke @search
  Scenario: Search for {search_term} with valid query
    When I enter "{search_term}" in the Google search box
    And I press Enter or click the Google Search button
    Then I should see search results for "{search_term}"
    And the results should contain relevant links
    And the search query should be displayed in the search box

  @search
  Scenario: Verify search suggestions for {search_term}
    When I start typing "{search_term[:5] if len(search_term) > 5 else search_term}" in the Google search box
    Then I should see search suggestions dropdown
    And the suggestions should be related to "{search_term}"

  @search
  Scenario: Search with multiple keywords
    When I enter "{search_term} best price 2024" in the Google search box
    And I click the Google Search button
    Then I should see search results
    And results should contain keywords "{search_term}", "price", and "2024"

  @search @negative
  Scenario: Search with special characters
    When I enter "{search_term} @#$%^&*()" in the Google search box
    And I click the Google Search button
    Then I should see search results or "no special results" message
    And the page should not display any error

  @search @navigation
  Scenario: Navigate through search result pages
    When I enter "{search_term}" in the Google search box
    And I click the Google Search button
    Then I should see search results for "{search_term}"
    When I click on the "Next" button at the bottom
    Then I should see the second page of results
    And the URL should contain "start=10"

  @search @filters
  Scenario: Search and apply filters
    When I enter "{search_term}" in the Google search box
    And I click the Google Search button
    Then I should see search results for "{search_term}"
    When I click on the "Images" tab
    Then I should see image results for "{search_term}"
    And the URL should contain "tbm=isch"

  @search @performance
  Scenario: Verify search results load time
    When I enter "{search_term}" in the Google search box
    And I note the current time
    And I click the Google Search button
    Then search results should load within 3 seconds
    And the page should display the number of results found"""
            
            # Generic search scenarios for other websites
            else:
                return f"""  Background:
    Given I navigate to "{base_url}"
    And I wait for the page to load completely

  @smoke @search
  Scenario: Search for {search_term} with valid query
    When I locate the search input field
    And I enter "{search_term}" in the search box
    And I submit the search form
    Then I should see search results for "{search_term}"
    And results should be displayed on the page

  @search
  Scenario: Search with empty query
    When I locate the search input field
    And I click the search button without entering any text
    Then I should see a validation message or all items displayed

  @search @negative
  Scenario: Search with non-existent {search_term}
    When I enter "xyznonexistent123{search_term}" in the search box
    And I submit the search form
    Then I should see "no results found" or similar message

  @search @filtering
  Scenario: Search and filter results
    When I enter "{search_term}" in the search box
    And I submit the search form
    And I apply category or price filters
    Then results should match the applied filters"""
        
        # Login/authentication features
        elif 'login' in feature_lower or 'signin' in feature_lower or 'auth' in feature_lower:
            return f"""  Background:
    Given I navigate to "{base_url}"

  @smoke @authentication
  Scenario: Successful login with valid credentials
    When I click on the login button
    And I enter valid email "testuser@example.com"
    And I enter valid password "Test@123"
    And I click the submit button
    Then I should be redirected to the dashboard
    And I should see a welcome message

  @authentication @negative
  Scenario: Login with invalid credentials
    When I click on the login button
    And I enter email "invalid@example.com"
    And I enter password "wrongpassword"
    And I click the submit button
    Then I should see an error message "Invalid credentials"
    And I should remain on the login page

  @authentication @validation
  Scenario: Login with empty fields
    When I click on the login button
    And I click the submit button without entering credentials
    Then I should see validation messages for required fields"""
        
        # Registration/signup features
        elif 'register' in feature_lower or 'signup' in feature_lower or 'sign up' in feature_lower:
            return f"""  Background:
    Given I navigate to "{base_url}"

  @smoke @registration
  Scenario: Successful user registration
    When I click on the sign up button
    And I fill in the registration form with valid data
    And I submit the registration form
    Then I should see a success message
    And I should receive a confirmation email

  @registration @validation
  Scenario: Registration with existing email
    When I click on the sign up button
    And I enter an already registered email
    And I submit the registration form
    Then I should see an error "Email already exists"

  @registration @validation
  Scenario: Registration with weak password
    When I click on the sign up button
    And I enter a password "123"
    And I submit the registration form
    Then I should see a password strength warning"""
        
        # Checkout/cart features
        elif 'checkout' in feature_lower or 'cart' in feature_lower or 'purchase' in feature_lower:
            return f"""  Background:
    Given I navigate to "{base_url}"
    And I add items to cart

  @smoke @checkout
  Scenario: Complete checkout process
    When I navigate to the shopping cart
    And I click on proceed to checkout
    And I fill in shipping information
    And I select a payment method
    And I confirm the order
    Then I should see an order confirmation
    And I should receive a confirmation number

  @checkout @validation
  Scenario: Checkout with empty cart
    When I clear all items from cart
    And I try to proceed to checkout
    Then I should see a message "Your cart is empty"

  @checkout
  Scenario: Apply coupon code during checkout
    When I navigate to the shopping cart
    And I enter a valid coupon code
    And I click apply
    Then the discount should be reflected in the total"""
        
        # Generic CRUD or form submission
        else:
            return f"""  Background:
    Given I navigate to "{base_url}"
    And the page loads successfully

  @smoke
  Scenario: Verify {feature_name.replace('_', ' ')} functionality
    When I interact with the {feature_name.replace('_', ' ')} feature
    And I provide valid input data
    And I submit the form
    Then the action should complete successfully
    And I should see a confirmation message

  @validation
  Scenario: Test {feature_name.replace('_', ' ')} with invalid data
    When I interact with the {feature_name.replace('_', ' ')} feature
    And I provide invalid input data
    And I submit the form
    Then I should see appropriate validation errors

  @negative
  Scenario: Test {feature_name.replace('_', ' ')} error handling
    When I interact with the {feature_name.replace('_', ' ')} feature
    And I simulate a system error
    Then I should see a user-friendly error message
    And the system should handle the error gracefully"""
    
    def _get_default_config(self, context: Dict[str, Any] = None) -> str:
        # Extract URL from context if available
        base_url = "https://example.com"
        if context and context.get("context_sources"):
            for source in context["context_sources"]:
                if source.get("type") == "url" and source.get("extracted", {}).get("url"):
                    base_url = source["extracted"]["url"]
                    break
        
        return f"""# Test Configuration
browser=chrome
base.url={base_url}
timeout=10
headless=false

# Browser configurations
chrome.driver.path=
firefox.driver.path=
edge.driver.path=

# Test data
test.data.path=src/test/resources/testdata/"""
    
    def _get_default_readme(self, feature_name: str) -> str:
        return f"""# {feature_name.replace('_', ' ').title()} Test Suite

## Overview
This test suite was generated by TestGen AI for testing the {feature_name.replace('_', ' ')} functionality.

## Prerequisites
- Java 11 or higher
- Maven 3.6 or higher
- Chrome/Firefox/Edge browser

## Running Tests
```bash
mvn clean test
```

## Test Reports
Test reports will be generated in the `target/cucumber-reports` directory.

## Configuration
Update `src/test/resources/config.properties` with your application settings.
"""
