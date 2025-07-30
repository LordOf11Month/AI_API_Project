

import os
from jinja2 import Template
from sqlalchemy import select
from app.DB_connection.database import get_db
from app.models.DBModels import PromptTemplate
from app.models.DataModels import SystemPrompt, PromptTemplateCreate
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# It's generally better to load file resources once, for example when the app starts.
# Reading at the module level is okay for simplicity but can have side effects.
isRootEnable = os.getenv('ROOT_PROMPT_ENABLE', 'true').lower() == 'true'

try:
    with open("app/root_prompt.txt", "r") as f:
        root_prompt_template_str = f.read()
    root_template = Template(root_prompt_template_str)

except FileNotFoundError:
    # Handle case where the root prompt file is missing
    root_template = Template("{{ client_systemprompt }}") # Fallback to a simple template


async def get_rendered_prompt(systemPrompt: SystemPrompt) -> str:
    '''
    Fetches a prompt template from the database, renders it with a root template,
    and returns the final prompt.
    '''
    async for db in get_db():
        # Use systemPrompt.template_name to match the Pydantic model
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == systemPrompt.template_name))
        db_template = result.scalars().first()

        if not db_template:
            # Handle case where the template is not found in the database
            raise ValueError(f"PromptTemplate with name '{systemPrompt.template_name}' not found.")

        # 1. Render the client-specific prompt from the DB using the tenants
        client_prompt_template = Template(db_template.prompt)
        rendered_client_prompt = client_prompt_template.render(systemPrompt.tenants)
        
        # 2. Render the root prompt using the result from the previous step
        if isRootEnable:
            final_prompt = root_template.render(client_systemprompt=rendered_client_prompt)
        else:
            print('[RENDERER] Warning!! root prompt disabled. open from env if needed')
            return rendered_client_prompt
        # Return a string as hinted
        return  final_prompt


async def create_prompt_template(template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Creates a new prompt template.
    Raises a ValueError if a template with the same name already exists.
    """
    async for db in get_db():
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == template_data.name))
        existing_template = result.scalars().first()

        if existing_template:
            raise ValueError(f"PromptTemplate with name '{template_data.name}' already exists.")

        new_template = PromptTemplate(
            name=template_data.name,
            prompt=template_data.prompt,
            tenant_fields=template_data.tenant_fields,
            version=1
        )
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        return new_template


async def update_prompt_template(template_name: str, template_data: PromptTemplateCreate) -> PromptTemplate:
    """
    Updates an existing prompt template.
    If the template exists, its version is incremented.
    Raises a ValueError if the template does not exist.
    """
    async for db in get_db():
        result = await db.execute(select(PromptTemplate).where(PromptTemplate.name == template_name))
        db_template = result.scalars().first()

        if not db_template:
            raise ValueError(f"PromptTemplate with name '{template_name}' not found.")
        
        # Update existing template
        db_template.prompt = template_data.prompt
        db_template.tenant_fields = template_data.tenant_fields
        db_template.version += 1
        db_template.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(db_template)
        return db_template
      