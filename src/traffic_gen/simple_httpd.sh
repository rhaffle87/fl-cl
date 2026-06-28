#!/bin/sh

# Start C2 Botnet listeners on 8080, 8888, and 9000 in the background
while true; do
  nc -lk -p 8080 -e sh -c 'printf "C2 OK\n"; sleep 0.1'
done >/dev/null 2>&1 &

while true; do
  nc -lk -p 8888 -e sh -c 'printf "C2 OK\n"; sleep 0.1'
done >/dev/null 2>&1 &

while true; do
  nc -lk -p 9000 -e sh -c 'printf "C2 OK\n"; sleep 0.1'
done >/dev/null 2>&1 &

# Main loop for Benign HTTP traffic on port 80
while true; do
  nc -lk -p 80 -e sh -c '
    read req
    echo "Request: $req" >> /tmp/httpd.log
    while read line; do
      clean_line=$(printf "%s" "$line" | tr -d "\r\n")
      if [ -z "$clean_line" ]; then
        break
      fi
    done
    printf "HTTP/1.1 200 OK\r\nContent-Length: 21\r\nConnection: close\r\n\r\nTarget Benign Server\n"
    sleep 1
  '
done

