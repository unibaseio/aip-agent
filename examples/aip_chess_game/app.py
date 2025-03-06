from flask import Flask, render_template_string
import chess.svg

app = Flask(__name__)


with open('chessboard.svg', 'r') as file:
    res = file.read()

@app.route('/')
def index():
    """主页面路由"""
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Auto Chess Board</title>
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
                
                // 每3秒刷新一次
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
