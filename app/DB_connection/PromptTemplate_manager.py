

import os
from uuid import UUID
from jinja2 import Template
from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import PromptTemplate
from app.models.DataModels import SystemPrompt, PromptTemplateCreate
from datetime import datetime, timezone
from dotenv import load_dotenv
from app.utils.console_logger import info, warning, error, debug


# Load environment variables from .env file
load_dotenv()

# It's generally better to load file resources once, for example when the app starts.
# Reading at the module level is okay for simplicity but can have side effects.
isRootEnable = os.getenv('ROOT_PROMPT_ENABLE', 'false').lower() == 'true'

try:
    with open("app/root_prompt.txt", "r") as f:
        root_prompt_template_str = f.read()
    root_template = Template(root_prompt_template_str)

except FileNotFoundError:
    # Handle case where the root prompt file is missing
    root_template = Template("{{ client_systemprompt }}") # Fallback to a simple template


async def get_rendered_prompt(system_prompt: SystemPrompt | None) -> str | None:
    """
    Renders a prompt template with the provided tenant data.
    """
    if not system_prompt:
        debug("No system prompt provided, returning None.", "[PromptManager]")
        return None

    info(f"Rendering prompt template: {system_prompt.template_name}", "[PromptManager]")
    async for db in get_db():
        result = await db.execute(
            select(PromptTemplate)
            .where(PromptTemplate.name == system_prompt.template_name)
        )
        template_record = result.scalars().first()

        if not template_record:
            warning(f"Prompt template not found: {system_prompt.template_name} empty template will be used", "[PromptManager]")
            system_prompt.template_name = "empty_template"
            system_prompt.tenants = {"SystemPrompt":""}
        
        # # Basic tenant field validation
        # for field in system_prompt.tenants:
        #     if field not in template_record.tenant_fields:
        #         error(f"Invalid tenant field '{field}' for template '{system_prompt.template_name}'\n valid template fields: {template_record.tenant_fields}", "[PromptManager]")
        #         raise ValueError(f"Invalid tenant field '{field}' for template '{system_prompt.template_name}'")

        # 1. Render the client-specific prompt from the DB using the tenants
        client_prompt_template = Template(template_record.prompt)
        rendered_client_prompt = client_prompt_template.render(system_prompt.tenants)
        
        # 2. Render the root prompt using the result from the previous step
        if isRootEnable:
            return root_template.render(client_systemprompt=rendered_client_prompt)
        else:
            warning('[RENDERER] Warning!! root prompt disabled. open from env if needed')
            return rendered_client_prompt


async def create_prompt_template(template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Creates a new prompt template.
    Raises a ValueError if a template with the same name already exists.
    """
    info(f"Attempting to create prompt template with name: {template_data.name}", "[PromptManager]")
    async for db in get_db():
        # Check if a template with the same name already exists
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == template_data.name))
        existing_template = result.scalars().first()
        if existing_template:
            error(f"Prompt template with name '{template_data.name}' already exists.", "[PromptManager]")
            raise ValueError(f"Prompt template with name '{template_data.name}' already exists.")

        new_template = PromptTemplate(
            name=template_data.name,
            prompt=template_data.prompt,
            tenant_fields=template_data.tenant_fields,
        )
        
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        info(f"Prompt template created successfully with ID: {new_template.name}", "[PromptManager]")
        return new_template

async def update_prompt_template(template_name: str, template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Updates an existing prompt template and its version is incremented.
    Raises a ValueError if the template does not exist.
    """
    info(f"Attempting to update prompt template: {template_name}", "[PromptManager]")
    async for db in get_db():
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == template_name))
        existing_template = result.scalars().first()

        if not existing_template:
            error(f"Prompt template not found for update: {template_name}", "[PromptManager]")
            raise ValueError(f"Prompt template '{template_name}' not found.")

        existing_template.prompt = template_data.prompt
        existing_template.tenant_fields = template_data.tenant_fields
        existing_template.version += 1
        
        await db.commit()
        await db.refresh(existing_template)
        info(f"Prompt template '{template_name}' updated successfully to version {existing_template.version}", "[PromptManager]")
        return existing_template
