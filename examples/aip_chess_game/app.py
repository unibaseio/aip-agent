from flask import Flask, render_template_string

app = Flask(__name__)


with open('chessboard.svg', 'r') as file:
    res = file.read()

@app.route('/')
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Auto Chess Board</title>
            <style>
                #board {
                    max-width: 80vw;
                    max-height: 80vh;
                    margin: 0 auto;
                }
                #board svg {
                    width: 100%;
                    height: 100%;
                }
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    padding: 0;
                    background-color: #f0f0f0;
                }
            </style>
        </head>
        <body>
            <div id="board">{{ svg|safe }}</div>
            
            <script>
                function refreshBoard() {
                    fetch('/show_board')
                        .then(response => response.text())
                        .then(svg => {
                            document.getElementById('board').innerHTML = svg;
                        });
                }
                
                // refresh the board every 3 seconds
                setInterval(refreshBoard, 3000);
            </script>
        </body>
        </html>
    ''', svg=res)

@app.route('/show_board')
def show_board():
    with open('chessboard.svg', 'r') as file:
        svg_content = file.read()
    return svg_content

if __name__ == "__main__":
    app.run(debug=True)
