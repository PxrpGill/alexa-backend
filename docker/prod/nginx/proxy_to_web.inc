# proxy_pass через переменную заставляет nginx резолвить `web` на каждый запрос
# (см. resolver в default.conf), поэтому пересозданный контейнер подхватывается
# без перезапуска nginx. Именованный upstream {} так НЕ работает.
set $upstream_web http://web:8000;
proxy_pass $upstream_web;

proxy_set_header Host              $host;
proxy_set_header X-Real-IP         $remote_addr;
proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_read_timeout 60;
