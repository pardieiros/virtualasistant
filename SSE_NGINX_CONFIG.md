# Configuração Nginx para Server-Sent Events (SSE)

Este documento descreve as configurações necessárias no Nginx para suportar streaming SSE do endpoint `/api/chat/stream/`.

## Problema

Por padrão, o Nginx bufferiza as respostas antes de enviá-las ao cliente. Para SSE funcionar corretamente, precisamos desativar este buffering e aumentar alguns timeouts.

## Configuração Recomendada

### 1. Location Block para SSE

Adiciona esta configuração ao teu bloco `server` ou `location /api/`:

```nginx
location /api/chat/stream/ {
    # Proxy para o backend Django
    proxy_pass http://backend:8000;
    
    # Headers necessários para SSE
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CRÍTICO: Desativar buffering para SSE
    proxy_buffering off;
    proxy_cache off;
    
    # Respeitar header do Django
    proxy_set_header X-Accel-Buffering no;
    
    # Aumentar timeouts para streams longos
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    proxy_send_timeout 300s;
    
    # Flush imediato
    proxy_request_buffering off;
    
    # Headers de resposta SSE
    add_header Cache-Control 'no-cache';
    add_header X-Accel-Buffering 'no';
}
```

### 2. Configuração Global (Opcional)

Se quiseres aplicar a todas as rotas `/api/`:

```nginx
location /api/ {
    proxy_pass http://backend:8000;
    
    # Headers básicos
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Para endpoints SSE apenas
    if ($request_uri ~* "^/api/chat/stream/") {
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

### 3. Configuração Docker Compose

No `docker-compose.yml`, certifica-te que o Nginx tem as configurações corretas:

```yaml
nginx:
  image: nginx:alpine
  container_name: virtualasistant_nginx
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./frontend/dist:/usr/share/nginx/html:ro
  depends_on:
    - backend
  networks:
    - virtualasistant
  restart: unless-stopped
```

## Exemplo Completo (nginx.conf)

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logs
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # Frontend (React)
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # API endpoints normais
        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts padrão
            proxy_read_timeout 60s;
            proxy_connect_timeout 60s;
        }

        # SSE streaming endpoint
        location /api/chat/stream/ {
            proxy_pass http://backend;
            
            # Headers
            proxy_http_version 1.1;
            proxy_set_header Connection '';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Desativar buffering (CRÍTICO para SSE)
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header X-Accel-Buffering no;
            
            # Timeouts longos para streaming
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
            proxy_send_timeout 300s;
            
            # Flush imediato
            proxy_request_buffering off;
            
            # Headers de resposta
            add_header Cache-Control 'no-cache';
            add_header X-Accel-Buffering 'no';
        }

        # Django static files
        location /static/ {
            alias /app/staticfiles/;
        }

        # Django media files
        location /media/ {
            alias /app/media/;
        }
    }
}
```

## Verificação

### 1. Testar SSE via curl

```bash
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!"}' \
  http://localhost/api/chat/stream/
```

Deves ver chunks a chegar incrementalmente, não tudo de uma vez.

### 2. Verificar Headers no Browser

Abre DevTools → Network → clica no request `/api/chat/stream/`

**Response Headers esperados:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

### 3. Logs do Nginx

```bash
docker logs virtualasistant_nginx -f
```

Se vires warnings sobre buffering, ajusta a config.

## Troubleshooting

### Problema: Chunks não chegam incrementalmente

**Causa:** Buffering ativo no Nginx.

**Solução:**
1. Verifica que `proxy_buffering off;` está presente
2. Verifica que `X-Accel-Buffering: no` header está a ser enviado
3. Reinicia o Nginx: `docker restart virtualasistant_nginx`

### Problema: Connection timeout após alguns segundos

**Causa:** Timeouts muito curtos.

**Solução:**
- Aumenta `proxy_read_timeout` para pelo menos 300s
- Aumenta `proxy_send_timeout` também

### Problema: 502 Bad Gateway durante stream

**Causa:** Backend Django crashou ou timeout.

**Solução:**
1. Verifica logs do Django: `docker logs virtualasistant_backend -f`
2. Verifica se o Ollama está a responder
3. Aumenta timeout do Django (Gunicorn: `--timeout 300`)

## Performance Tips

1. **Chunked Transfer Encoding:** SSE usa automaticamente, não precisas configurar
2. **Connection Pooling:** Nginx mantém conexões persistentes com o backend
3. **Worker Connections:** Aumenta se tiveres muitos utilizadores simultâneos:
   ```nginx
   events {
       worker_connections 4096;
   }
   ```

## Referências

- [Nginx Proxy Buffering](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_buffering)
- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Django StreamingHttpResponse](https://docs.djangoproject.com/en/stable/ref/request-response/#streaminghttpresponse-objects)
















