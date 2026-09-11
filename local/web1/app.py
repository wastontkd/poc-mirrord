from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        print(f"Requisicao recebida localmente: {self.path}")

        body = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WEB1 Local</title>
        </head>
        <body>
            <h1>WEB1 LOCAL</h1>
            <h2>Executando atraves do mirrord</h2>
            <p>
                Esta aplicação está rodando no computador
                do desenvolvedor.
            </p>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

        self.wfile.write(body.encode())


server = HTTPServer(
    ("0.0.0.0", 8080),
    Handler
)

print("WEB1 LOCAL escutando na porta 8080")

server.serve_forever()