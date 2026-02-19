"""
Deployment clients using your configured tokens:
- VERCEL_TOKEN
"""

import os
import json
from typing import Any, Dict, Optional, List


class VercelClient:
    """Client for Vercel deployments."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv('VERCEL_TOKEN')
        self.api_url = "https://api.vercel.com"
    
    async def deploy(self, 
                     project_name: str, 
                     files: Dict[str, str],
                     environment: str = "production") -> Dict[str, Any]:
        """
        Deploy files to Vercel.
        
        Args:
            project_name: Vercel project name
            files: Dict of {filename: content}
            environment: production or preview
        
        Returns:
            Deployment info
        """
        if not self.token:
            return {"success": False, "error": "VERCEL_TOKEN not configured"}
        
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            
            # Create deployment
            payload = {
                "name": project_name,
                "files": [
                    {"file": name, "data": content}
                    for name, content in files.items()
                ],
                "target": environment if environment == "production" else None
            }
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_url}/v13/deployments",
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                ) as resp:
                    data = await resp.json()
                    
                    if resp.status == 200:
                        return {
                            "success": True,
                            "url": data.get("url"),
                            "id": data.get("id"),
                            "state": data.get("state")
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error", {}).get("message", "Unknown error"),
                            "status": resp.status
                        }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_project(self, project_name: str) -> Dict[str, Any]:
        """Get project info."""
        if not self.token:
            return {"success": False, "error": "VERCEL_TOKEN not configured"}
        
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.api_url}/v9/projects/{project_name}",
                    headers={"Authorization": f"Bearer {self.token}"}
                ) as resp:
                    if resp.status == 200:
                        return {"success": True, "data": await resp.json()}
                    else:
                        return {"success": False, "status": resp.status}
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
    
    async def list_deployments(self, project_name: str, limit: int = 10) -> List[Dict]:
        """List recent deployments."""
        if not self.token:
            return []
        
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.api_url}/v6/deployments",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"projectId": project_name, "limit": limit}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("deployments", [])
                    return []
        except aiohttp.ClientError:
            return []
