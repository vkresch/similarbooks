# Server Setup

passwd root
sudo apt update && upgrade
sudo apt install ufw


## Setup ssh public/private key

## Setup non-privileged user
useradd viktor
adduser viktor sudo

## Setup the firewall
sudo ufw default allow outgoing
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 8000
sudo ufw allow 9797
sudo ufw enable
sudo ufw status

## Install bazel
wget https://github.com/bazelbuild/bazel/releases/download/7.0.1/bazel-7.0.1-installer-linux-x86_64.sh
chmod +x bazel-7.0.1-installer-linux-x86_64.sh
./bazel-7.0.1-installer-linux-x86_64.sh --user
ln /home/viktor/bin/bazel bazel /usr/bin/bazel
bazel --version

## Clone the repo
git clone https://github.com/vkresch/similarbooks.git

## Setup mongodb
Source: https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/
https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-20-04

curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
   --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install mongodb-org
sudo systemctl start mongod.service
sudo systemctl status mongod
sudo systemctl enable mongod
mongosh --eval 'db.runCommand({ connectionStatus: 1 })'

## Convert MongoDB to replica set to use change streams
https://www.mongodb.com/docs/manual/tutorial/convert-standalone-to-replica-set/

and create a mongoreplica.keyfile
https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/

openssl rand -base64 756 > mongoreplica.keyfile
sudo cp mongoreplica.keyfile /etc/ssl/mongodb/
sudo chmod 400 /etc/ssl/mongodb/mongoreplica.keyfile
sudo chown mongodb:mongodb /etc/ssl/mongodb/mongoreplica.keyfile

## App dependencies
sudo apt install libffi-dev build-essential libpng-dev libfontconfig1-dev python-is-python3 libxml2-dev libxslt-dev python3-numpy python3-sklearn python3-pip

## Copy artifacts like model and scalers
scp -P 9797 *.pkl viktor@164.90.230.40:/home/viktor/similarbooks/som/models
scp -r -P 9797 viktor@164.90.230.40:/home/viktor/backup/similarbooks /home/vkreschenski/Documents/Privat/Freelancer/backup
scp -o IdentitiesOnly=yes -r /home/vkreschenski/Documents/Privat/Freelancer/backup/similarbooks/similarbooks/* viktor@similarbooks.net:/home/viktor/data

## Create certificate
openssl req -newkey rsa:2048 -new -x509 -days 1825 -nodes -out mongodb.crt -keyout mongodb.key -subj "/CN=31.220.93.169/C=DE/ST=Bayern/L=Burgkirchen/O=Kretronik GmbH" -addext "subjectAltName=IP:31.220.93.169,IP:127.0.0.1,DNS:localhost"

cat mongodb.key mongodb.crt > mongodb.pem
sudo mkdir -p /etc/ssl/mongodb
sudo cp mongodb.pem /etc/ssl/mongodb
sudo cp mongodb.crt /etc/ssl/mongodb

Create admin user and simple spider user
use admin
db.createUser({user: "username", pwd: "password", roles: [ { role: "userAdminAnyDatabase", db: "admin" }, { role: "readWrite", db: "similarbooks" }, { role: "root", db: "admin" } ]})

use similarbooks
db.createUser({user: "username", pwd: "password", roles: [ { role: "readWrite", db: "similarbooks" } ]})

sudo vim /etc/mongodb/mongod.conf
```
net:
  port: 27017
  bindIp: 127.0.0.1,164.90.230.40
  tls:
    mode: requireTLS
    certificateKeyFile: /etc/ssl/mongodb/mongodb.pem
    CAFile: /etc/ssl/mongodb/mongodb.crt

security:
    authorization: enabled
    keyFile: /etc/ssl/mongodb/mongoreplica.keyfile
```
https://gist.github.com/achesco/b7cf9c0c93186c4a7362fb4832c866c0

Make sure mongodb has the correct access rights to the keyfile:
sudo chown -R mongodb:mongodb /etc/ssl/mongodb/mongoreplica.keyfile

## Restore db mongo local (Existing ObjectID will NOT be overwritten)
cd /home/vkreschenski/Documents/Privat/Freelancer/backup
mongorestore --uri "mongodb://$MONGODB_SOMANTIC_USER:$MONGODB_SOMANTIC_PWD@$MONGODB_SOMANTIC_URL:27017/similarbooks?authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem" --db similarbooks --verbose .

# Dump mongodb
mongodump --uri="mongodb://$MONGODB_SOMANTIC_USER:$MONGODB_SOMANTIC_PWD@$MONGODB_SOMANTIC_URL:27017/similarbooks?authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem" --out=.

## MongoDB Query
mongosh "mongodb://$MONGODB_SOMANTIC_USER:$MONGODB_SOMANTIC_PWD@$MONGODB_SOMANTIC_URL:27017/similarbooks?authMechanism=DEFAULT&authSource=similarbooks&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem"

Show Users:
db.getCollection('user').find({})

Show User Count:
db.getCollection('user').countDocuments()

Show appartment count:
db.getCollection('appartment').countDocuments()

Show house count:
db.getCollection('house').countDocuments()

## Test the application
set DEBUG=False in constant.py

## Setup nginx and gunicorn
sudo apt install python3-venv
python3 -m venv venv
sudo apt install nginx
sudo pip3 install gunicorn
sudo rm /etc/nginx/sites-enabled/default
sudo vim /etc/nginx/sites-enabled/similarbooks

sudo chmod -R 755 /home/viktor/similarbooks/app/similarbooks/static
sudo chown -R www-data:www-data /home/viktor/similarbooks/app/similarbooks/static

```
server{
   server_name www.similarbooks.net;
   location /static {
         alias /home/viktor/similarbooks/app/similarbooks/static;
    }
    location / {
        proxy_pass http://localhost:8000;
        include /etc/nginx/proxy_params;
        proxy_redirect off;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/www.similarbooks.net/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/www.similarbooks.net/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}
server {
    listen       80;
    server_name  similarbooks.net;
    return       301 https://www.similarbooks.net$request_uri;
}
server{
    if ($host = www.similarbooks.net) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

   listen 80;
   server_name www.similarbooks.net;
    return 404; # managed by Certbot

}
```
sudo ufw allow http/tcp
sudo ufw delete allow 8000
sudo ufw enable
sudo ufw status
sudo systemctl restart nginx

## CSS work around
sudo vim /etc/nginx/nginx.conf
user viktor;

## Setup certbot
Source: https://certbot.eff.org/
