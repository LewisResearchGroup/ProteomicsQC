# Instructions will be added soon.

> In order to run the server on a specific domain you have to register the domain
> and point it to the public IP address of your server. Furthermore, you have to 
> setup a remote proxy to redirect HTTP and HTTPS requests to port 8080. 
> For security reasons you should always use HTTPS. The server was tested using
> a remote proxy configured with NGINX and for encryption we used letsencrypt and 
> certbot.

# Setup a public server

## DNS entry

## SSL certificate (letsencrypt)

## Remote proxy NGINX


## NGINX configuration example

Here is an example configuration file `/etc/nginx/sites-enabled/proteomics-qc`:

This example assumes that files are stored under `/mnt/data/static/` and `/mnt/data/datalake/`.
Which can be set in the configuration file (`.env`). 

```
server {
  listen 443 ssl;
  listen [::]:443 ssl;

  server_name example.com;

  ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem; # managed by Certbot
  ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem; # managed by Certbot
  ssl_protocols TLSv1.2 TLSv1.3;

  root /var/www/html;
  index index.html index.htm index.nginx-debian.html;

  access_log    /var/log/nginx/ProteomicsQC.access.log;
  error_log     /var/log/nginx/ProteomicsQC.error.log;

  location / {
    proxy_pass              http://localhost:8080;
    client_max_body_size    100G;

    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header Host $host;
 }

  location /static/ {
    root /mnt/data/;
    autoindex on;
  }

  location /datalake/ {
    root /mnt/data/;
    autoindex on;
  }  
}


server {
  listen 80;
  listen [::]:80;
  server_name example.com www.example.com;
  return 301 https://$server_name$request_uri;
}
```