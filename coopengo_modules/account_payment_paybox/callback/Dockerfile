FROM node:8-alpine

RUN mkdir paybox-callback

WORKDIR paybox-callback

COPY package.json *.js ./

RUN npm i --production

EXPOSE 3000
    
ENTRYPOINT ["node", "."]
