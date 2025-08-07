"""
Prompt Template Management Module

This module provides functions for managing and rendering prompt templates from
the database. It uses Jinja2 for templating and supports a two-layered rendering
process with an optional root prompt.

Key Functions:
- get_rendered_prompt: Renders a prompt template with provided data, optionally
  wrapping it with a root prompt.
- create_prompt_template: Creates a new prompt template in the database.
- update_prompt_template: Updates an existing prompt template.

Author: Ramazan Seçilmiş
Version: 1.0.0
"""


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
    warning("Root prompt file not found, using default template", "[PromptManager]")
    root_template = Template("{{ client_systemprompt }}") # Fallback to a simple template


async def get_rendered_prompt(system_prompt: SystemPrompt | None) -> str | None:
    """
    Renders a prompt template with provided data, optionally wrapping it with a root prompt.
    
    This function fetches a prompt template from the database, renders it with
    the provided tenant data, and then optionally renders a root prompt using
    the result.
    
    Args:
        system_prompt (SystemPrompt | None): The system prompt object containing
                                             the template name and tenant data.
                                             
    Returns:
        str | None: The fully rendered prompt text, or None if no system prompt
                    is provided.
    """
    try:
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

            # # Basic tenant field validation
            # for field in system_prompt.tenants:
            #     if field not in template_record.tenant_fields:
            #         error(f"Invalid tenant field '{field}' for template '{system_prompt.template_name}'\n valid template fields: {template_record.tenant_fields}", "[PromptManager]")
            #         raise ValueError(f"Invalid tenant field '{field}' for template '{system_prompt.template_name}'")

            # 1. Render the client-specific prompt from the DB using the tenants
            if not template_record:
                warning(f"Prompt template not found: {system_prompt.template_name} empty template will be used", "[PromptManager]")
                rendered_client_prompt = ""
            else:
                client_prompt_template = Template(template_record.prompt)
                rendered_client_prompt = client_prompt_template.render(system_prompt.tenants)
            
            # 2. Render the root prompt using the result from the previous step
            if isRootEnable:
                return root_template.render(client_systemprompt=rendered_client_prompt)
            else:
                    warning('[RENDERER] Warning!! root prompt disabled. open from env if needed')
                    return rendered_client_prompt
    except Exception as e:
        error(f"Error rendering prompt template at line {e.__traceback__.tb_lineno}: {e}", "[PromptManager]")
        raise e


async def create_prompt_template(template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Creates a new prompt template in the database.
    
    Args:
        template_data (PromptTemplateCreate): The data for the new template.
        
    Returns:
        PromptTemplate: The newly created prompt template object.
        
    Raises:
        ValueError: If a template with the same name already exists.
    """
    info(f"Attempting to create prompt template with name: {template_data.name}", "[PromptManager]")
    try:
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
    except Exception as e:
        error(f"Error creating prompt template at line {e.__traceback__.tb_lineno}: {e}", "[PromptManager]")
        raise e

async def update_prompt_template(template_name: str, template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Updates an existing prompt template in the database.
    
    Args:
        template_name (str): The name of the template to update.
        template_data (PromptTemplateCreate): The new data for the template.
        
    Returns:
        PromptTemplate: The updated prompt template object.
        
    Raises:
        ValueError: If the template does not exist.
    """
    info(f"Attempting to update prompt template: {template_name}", "[PromptManager]")
    try:
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
    except Exception as e:
        error(f"Error updating prompt template at line {e.__traceback__.tb_lineno}: {e}", "[PromptManager]")
        raise e
