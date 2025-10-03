# AI Prompts - ReviewAssist Pro

This directory contains AI prompts and templates used throughout the ReviewAssist Pro project.

## Current Prompts

### Review Response Generation
The main AI functionality uses OpenAI API to generate contextual responses to customer reviews. Prompts are dynamically constructed based on:
- Review sentiment (positive, negative, neutral)
- Response tone (professional, friendly, apologetic, grateful)
- Business context and review content

### Development Assistance
AI assistants working on this project should reference:
- `docs/PREPRODUCTION.md` for project context
- `_meta/AI_GUIDE.md` for development guidelines
- `_meta/TASKS.md` for current priorities

## Adding New Prompts

When adding new AI prompts or templates:
1. Create descriptive filenames (e.g., `review_response_template.txt`)
2. Include context and usage instructions
3. Test prompts thoroughly before committing
4. Update this README with new prompt descriptions

## Prompt Engineering Guidelines

- Be specific and clear in prompt instructions
- Include examples when helpful
- Consider edge cases and error handling
- Test with various input scenarios
- Document prompt performance and iterations

