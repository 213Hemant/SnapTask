#!/usr/bin/env bash
npm install
npx tailwindcss -i ./static/src/input.css -o ./static/dist/output.css --minify
