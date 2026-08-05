import os
import logging
from app.services.docker_service import DockerService

logger = logging.getLogger(__name__)

class NginxService:
    CONFIG_DIR = "/app/nginx/conf.d/apps"
    
    @staticmethod
    def add_or_update_deployment(slug: str, container_name: str, port: int) -> None:
        """
        Creates an NGINX config snippet for the given deployment slug.
        """
        os.makedirs(NginxService.CONFIG_DIR, exist_ok=True)
        conf_path = os.path.join(NginxService.CONFIG_DIR, f"{slug}.conf")
        
        config = f"""
location /apps/{slug}/ {{
    rewrite ^/apps/{slug}/(.*) /$1 break;
    rewrite ^/apps/{slug}$ / break;
    proxy_pass http://{container_name}:{port};
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_addrs;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Websocket support
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}}
"""
        with open(conf_path, "w") as f:
            f.write(config)
            
        NginxService.reload()

    @staticmethod
    def remove_deployment(slug: str) -> None:
        conf_path = os.path.join(NginxService.CONFIG_DIR, f"{slug}.conf")
        if os.path.exists(conf_path):
            os.remove(conf_path)
            NginxService.reload()

    @staticmethod
    def reload() -> None:
        client = DockerService._get_client()
        try:
            container = client.containers.get("bonk-nginx")
            res = container.exec_run("nginx -s reload")
            if res.exit_code != 0:
                logger.error(f"Failed to reload NGINX: {{res.output.decode('utf-8')}}")
            else:
                logger.info("NGINX reloaded successfully")
        except Exception as e:
            logger.error(f"Error executing NGINX reload: {{e}}")
