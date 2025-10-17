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
                    if api_key:
                        # Initialize OpenAI client with minimal parameters
                        try:
                            # Initialize OpenAI client
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
                    if api_key:
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
        test_files = self._parse_generated_content(generated_content, feature_name)
        
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
    
    def _parse_generated_content(self, content: str, feature_name: str) -> Dict[str, str]:
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
            files = self._create_default_test_structure(feature_name, content)
        
        return files
    
    def _create_default_test_structure(self, feature_name: str, content: str) -> Dict[str, str]:
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
        return f"""package com.testgen.stepdefinitions;

import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.And;
import org.junit.Assert;

public class {feature_name.title().replace('_', '')}Steps {{
    
    @Given("I am on the application homepage")
    public void i_am_on_the_application_homepage() {{
        // Implementation for navigating to homepage
    }}
    
    @When("I perform the main action")
    public void i_perform_the_main_action() {{
        // Implementation for main action
    }}
    
    @Then("I should see the expected result")
    public void i_should_see_the_expected_result() {{
        // Implementation for verification
        Assert.assertTrue("Expected result not found", true);
    }}
}}"""
    
    def _get_default_feature_file(self, feature_name: str, content: str, context: Dict[str, Any] = None) -> str:
        # Extract URL from context if available
        base_url = "the application homepage"
        if context and context.get("context_sources"):
            for source in context["context_sources"]:
                if source.get("type") == "url" and source.get("extracted", {}).get("url"):
                    url = source["extracted"]["url"]
                    title = source["extracted"].get("title", "")
                    base_url = f"the {title} page at {url}" if title else f"the page at {url}"
                    break
        
        return f"""Feature: {feature_name.replace('_', ' ').title()}
  As a user
  I want to test the {feature_name.replace('_', ' ')} functionality
  So that I can ensure it works correctly

  Scenario: Basic functionality test
    Given I am on {base_url}
    When I perform the main action
    Then I should see the expected result

  Scenario: Error handling test
    Given I am on {base_url}
    When I perform an invalid action
    Then I should see an error message

  # Generated based on context:
  # {content[:200]}..."""
    
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
