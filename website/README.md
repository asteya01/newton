# Newton website

Static HTML pages, no build step needed to host them. Upload everything in this folder (plus `newton.zip` and `newton-intro.mp4`) to Cloudflare Pages.

`source/` holds the generators that produce the pages. Run `bash source/buildall.sh` from a folder containing `three.min.js`, `newton.zip` and the files in `source/`.
