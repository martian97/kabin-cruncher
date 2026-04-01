FROM node:20-bullseye

# Install system deps: Python + ffmpeg for the compression scripts
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy both the Next.js app and the Python compression skills
COPY media-compressor-app ./media-compressor-app
COPY image-and-video-compression-skills ./image-and-video-compression-skills

WORKDIR /app/media-compressor-app

# Install Node dependencies
RUN npm install

# Install Python deps for image compression
RUN pip3 install --no-cache-dir Pillow

# Build Next.js for production
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]

