const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8000;

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
};

const server = http.createServer((req, res) => {
  // Normalize URL to prevent directory traversal
  const safeUrl = path.normalize(req.url).replace(/^(\.\.[\/\\])+/, '');
  let filePath = path.join(__dirname, safeUrl);

  if (req.url === '/') {
    filePath = path.join(__dirname, 'index.html');
  }

  const extname = String(path.extname(filePath)).toLowerCase();
  const contentType = MIME_TYPES[extname] || 'application/octet-stream';

  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        res.writeHead(404);
        res.end('Not Found');
      } else {
        res.writeHead(500);
        res.end('Internal Error: ' + error.code);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

server.listen(PORT, () => {
  console.log(`Starting server...`);
  console.log(`Open http://localhost:${PORT} in your browser.`);
});
