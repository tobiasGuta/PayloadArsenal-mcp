import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PayloadArsenal")

ARSENAL_DIR = "/opt/arsenal"

@mcp.tool()
def search_arsenal_files(query: str) -> str:
    """
    Search for payload files or wordlists by name in PayloadsAllTheThings and SecLists.
    
    Args:
        query: The keyword to search for (e.g., 'xss', 'sqli', 'api', 'lfi')
    """
    try:
        # Case-insensitive search for files matching the query
        result = subprocess.run(
            ["find", ARSENAL_DIR, "-type", "f", "-iname", f"*{query}*"],
            capture_output=True, text=True, check=False
        )
        files = result.stdout.strip().split('\n')
        files = [f for f in files if f and os.path.isfile(f)]
        
        if not files:
            return f"No files found matching '{query}'."
            
        # Limit results to prevent overwhelming the LLM context
        if len(files) > 50:
            return f"Found {len(files)} files. Showing first 50:\n" + "\n".join(files[:50])
            
        return f"Found {len(files)} files:\n" + "\n".join(files)
        
    except Exception as e:
        return f"Error searching files: {str(e)}"

@mcp.tool()
def read_arsenal_file(filepath: str, max_lines: int = 500) -> str:
    """
    Read the contents of a payload Markdown file or a wordlist.
    
    Args:
        filepath: The full absolute path to the file (must start with /opt/arsenal)
        max_lines: Max number of lines to return (default 500 to prevent context overflow on massive wordlists)
    """
    try:
        # Guard against path traversal
        real_path = os.path.realpath(filepath)
        if not real_path.startswith(ARSENAL_DIR):
            return "Error: Access outside the arsenal directory is not permitted."
            
        if not os.path.exists(real_path) or not os.path.isfile(real_path):
            return f"Error: File not found at {real_path}"
            
        with open(real_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    lines.append(f"\n... [File truncated at {max_lines} lines to save context] ...")
                    break
                lines.append(line.rstrip("\n"))
                
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def search_payload_content(query: str) -> str:
    """
    Grep for specific payload strings inside all PayloadsAllTheThings Markdown files.
    Useful when you know what you want but don't know the exact file name.
    
    Args:
        query: The string to search for (e.g., 'alert(1)', 'UNION SELECT')
    """
    try:
        # grep -ri "query" /opt/arsenal/PayloadsAllTheThings --include="*.md"
        result = subprocess.run(
            ["grep", "-ri", query, f"{ARSENAL_DIR}/PayloadsAllTheThings", "--include=*.md", "-m", "15"],
            capture_output=True, text=True, check=False
        )
        output = result.stdout.strip()
        
        if not output:
            return f"No matches found for '{query}' in payload contents."
            
        if len(output) > 4000:
            output = output[:4000] + "\n... [Output truncated due to size] ..."
            
        return output
        
    except Exception as e:
        return f"Error searching content: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')