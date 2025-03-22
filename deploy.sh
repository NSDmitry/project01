docker build --platform=linux/amd64 -t project01 .
docker tag project01 nsdmitrij/project01:latest
docker push nsdmitrij/project01:latest