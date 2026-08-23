import os

def classify_role(file_path: str) -> str:
    """
    Analyzes a file path and determines its architectural role.
    This logic is extracted and adapted from the old DocSwarm implementation.
    """
    path_lower = file_path.lower()
    name = os.path.basename(path_lower)
    
    if name in ['main.py', 'index.js', 'app.tsx', 'app.ts', 'server.js', 'cli.py']:
        return "Entry Points"
        
    if any(k in path_lower for k in ['route', 'api', 'endpoint', 'controller']):
        return "Routing & Controllers"
        
    if any(k in path_lower for k in ['model', 'schema', 'db', 'database', 'entity']):
        return "Data Models & Persistence"
        
    if any(k in path_lower for k in ['service', 'logic', 'manager', 'util', 'helper', 'core']):
        return "Services & Utilities"
        
    if any(k in path_lower for k in ['component', 'ui', 'view', 'page', 'screen']):
        return "UI Components"
        
    if name.endswith(('.json', '.yaml', '.yml', '.env', '.toml', 'config.js', 'config.ts', 'requirements.txt')):
        return "Configuration"
        
    if name.endswith(('.md', '.txt', '.rst')):
        return "Documentation"
        
    return "Other"
