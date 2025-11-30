# Document Generator MCP Server

A Model Context Protocol (MCP) server that generates Word, Excel, and PowerPoint documents with template support.

## Purpose

This MCP server provides a secure interface for AI assistants to generate professional documents in various formats using templates.

## Features

### Current Implementation
- **`document_generate_word`** - Generate Word documents with text content and optional templates
- **`document_generate_excel`** - Generate Excel spreadsheets with data and optional templates
- **`document_generate_powerpoint`** - Generate PowerPoint presentations with slides and optional templates
- **`document_generate_pdf`** - Generate PDF documents with text content

## Prerequisites

- Docker Desktop with MCP Toolkit enabled
- Docker MCP CLI plugin (`docker mcp` command)
- Template files (optional) placed in /app/templates/ directory

## Installation

See the step-by-step instructions provided with the files.

## Usage Examples

In copilot CLI, you can ask:

- "Generate a Word document with the content 'Hello World' using template 'report.docx'"
- "Create an Excel spreadsheet with data [['Name', 'Age'], ['John', 30], ['Jane', 25]]"
- "Make a PowerPoint presentation with slides [{'title': 'Introduction', 'content': 'Welcome'}, {'title': 'Conclusion', 'content': 'Thank you'}]"
- "Generate a PDF document with the content 'This is a sample PDF report'"

## Architecture

```
copilot CLI → MCP Gateway → Document Generator MCP Server → Document Libraries
↓
Docker Desktop (Templates in /app/templates/, Outputs in /app/outputs/)
```

## Development

### Local Testing

```bash
# Set environment variables for testing
export DOCUMENT_API_TOKEN="test-value"

# Run directly
python document_server.py

# Test MCP protocol
echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python document_server.py
```

### Adding New Tools

1. Add the function to `document_server.py`
2. Decorate with `@mcp.tool()`
3. Update the catalog entry with the new tool name
4. Rebuild the Docker image

## Troubleshooting

### Tools Not Appearing
- Verify Docker image built successfully
- Check catalog and registry files
- Ensure copilot CLI config includes custom catalog
- Restart copilot CLI

### Template Errors
- Ensure template files are copied to /app/templates/ in the Docker image
- Verify template file formats match the document type

### File Access
- Mount host directories to /app/outputs/ to access generated files
- Check file permissions for the mcpuser

## Security Considerations

- All operations run in isolated Docker container
- No external API calls or network access
- Running as non-root user
- Templates and outputs stored in container filesystem

## License

MIT License