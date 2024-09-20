FROM squidfunk/mkdocs-material:latest as build

ADD docs /docs/docs
ADD mkdocs.yml /docs/mkdocs.yml
RUN pip install mkdocs-glightbox && \
  mkdocs build -d "/src"

FROM nginx:1.27.1-alpine
RUN rm -rf /usr/share/nginx/html
COPY --from=build /src /usr/share/nginx/html

EXPOSE 80
