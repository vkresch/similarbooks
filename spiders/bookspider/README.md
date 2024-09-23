# Spiders

```
bazel run //spiders/bookspider:bookspider
```

## Create spider user in mongodb
openssl req -newkey rsa:2048 -new -x509 -days 1825 -nodes -out mongodb.crt -keyout mongodb.key -subj "/CN=185.245.182.5/C=DE/ST=Bayern/L=Burgkirchen/O=Kretronik GmbH" -addext "subjectAltName=IP:185.245.182.5,IP:127.0.0.1,DNS:localhost"

cat mongodb.key mongodb.crt > mongodb.pem
sudo mkdir -p /etc/ssl/mongodb
sudo cp mongodb.pem /etc/ssl/mongodb
sudo cp mongodb.crt /etc/ssl/mongodb

Create admin user and simplespider user
use admin
db.createUser({user: "admin", pwd: "password", roles: [ { role: "userAdminAnyDatabase", db: "admin" }, { role: "readWrite", db: "similarbooks" }, { role: "root", db: "admin" } ]})

use similarbooks
db.createUser({user: "simplespider", pwd: "password", roles: [ { role: "readWrite", db: "similarbooks" } ]})